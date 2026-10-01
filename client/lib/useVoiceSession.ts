"use client";

import { useCallback, useRef, useState } from "react";
import { connectVoiceSocket, gatewayWsUrl, type InterviewParams, type OrbState, type Question } from "./ws";
import { Player, audioLevel, startMic, startRecording } from "./audio";
import { feedback } from "./feedback";

export type SessionState = OrbState | "disconnected";
// mic/no-mic: couldn't get the microphone; unreachable: socket never opened; dropped: lost mid-call;
// busy: the gateway is at its session cap and refused the call
// refused: not allowed to start this interview; no-credits: out of mocks
export type ErrorKind = "mic" | "no-mic" | "unreachable" | "dropped" | "busy" | "refused" | "no-credits";

// server/gateway/ws_handler.py
const CLOSE_ERRORS: Record<number, ErrorKind> = { 1013: "busy", 1008: "refused", 4402: "no-credits" };
// An interview whose connection drops is reconnected after these delays (ms). The server keeps it for 60s.
const RECONNECT_DELAYS = [1000, 3000, 6000, 10000, 15000];

export interface Turn {
  role: "user" | "assistant";
  text: string;
}

type Mic = Awaited<ReturnType<typeof startMic>>;

// onRecording: when set, both sides of the call are recorded and handed over when the call ends.
export function useVoiceSession({ onRecording }: { onRecording?: (audio: Blob) => void } = {}) {
  const [state, setState] = useState<SessionState>("disconnected");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<ErrorKind | null>(null);
  const [interruptTick, setInterruptTick] = useState(0);
  const [muted, setMuted] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [question, setQuestion] = useState<Question | null>(null);
  const [interviewId, setInterviewId] = useState<string | null>(null); // set when the interviewer ends the call
  // time from "thinking" to first reply audio, ms: last turn + running average for this call
  const [latency, setLatency] = useState<{ last: number; avg: number; count: number } | null>(null);
  const thinkingAtRef = useRef<number | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const playerRef = useRef<Player | null>(null);
  const micRef = useRef<Mic | null>(null);
  const recorderRef = useRef<ReturnType<typeof startRecording> | null>(null);

  // Levels 0..1, polled per animation frame by the orb, not React state. getLevel (louder of the
  // two) drives the sphere; getMicLevel alone drives the "you're being heard" ring.
  const getMicLevel = useCallback(() => audioLevel(micRef.current?.analyser ?? null), []);
  const getLevel = useCallback(
    () => Math.max(getMicLevel(), audioLevel(playerRef.current?.analyser ?? null)),
    [getMicLevel],
  );

  // Release mic + audio output. Shared by user hang-up and dropped connections, so the mic never
  // stays live after a call ends. Idempotent: refs are nulled as they're released.
  const teardown = useCallback(() => {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    if (recorder && onRecording) void recorder.stop().then(onRecording);
    const mic = micRef.current;
    micRef.current = null;
    mic?.stream.getTracks().forEach((t) => t.stop());
    void mic?.ctx.close();
    playerRef.current?.close();
    playerRef.current = null;
    setMuted(false);
  }, [onRecording]);

  // End the current socket without its onClose treating it as a drop; shared by hang-up and failures.
  const closeSession = useCallback(
    (nextError: ErrorKind | null) => {
      const socket = socketRef.current;
      socketRef.current = null;
      socket?.close(1000); // 1000 = hung up on purpose: the server finishes the interview instead of waiting for a reconnect
      teardown();
      setState("disconnected");
      setConnecting(false);
      setReconnecting(false);
      setError(nextError);
    },
    [teardown],
  );

  const connect = useCallback(
    ({
      voice,
      keepTurns = false,
      interview,
    }: { voice?: string; keepTurns?: boolean; interview?: InterviewParams } = {}) => {
      setError(null);
      setInterviewId(null);
      if (!keepTurns) {
        setTurns([]);
        setQuestion(null);
      }
      setLatency(null);
      thinkingAtRef.current = null;
      setConnecting(true);
      playerRef.current = new Player(24000);
      const url = gatewayWsUrl(voice, interview);
      let attempt = 0;

      const open = () => {
        let opened = false;
        const socket = connectVoiceSocket(url, {
          onOpen: async () => {
            opened = true;
            attempt = 0;
            // a reconnect: the mic and recording kept running through the drop
            if (micRef.current) {
              setReconnecting(false);
              return;
            }
            try {
              const mic = await startMic((pcm16) => {
                const live = socketRef.current;
                if (live?.readyState === WebSocket.OPEN) live.send(pcm16);
              });
              // call ended while the permission prompt was open: release the mic we just got
              if (socketRef.current !== socket) {
                mic.stream.getTracks().forEach((t) => t.stop());
                void mic.ctx.close();
                return;
              }
              micRef.current = mic;
              if (onRecording && playerRef.current) recorderRef.current = startRecording(playerRef.current.mixWith(mic.stream));
              setState("idle");
              setConnecting(false);
              feedback("connect");
            } catch (err) {
              if (socketRef.current !== socket) return;
              closeSession(err instanceof DOMException && err.name === "NotFoundError" ? "no-mic" : "mic");
              feedback("error");
            }
          },
          onState: (s) => {
            if (s === "thinking") thinkingAtRef.current = performance.now();
            else if (s !== "speaking") thinkingAtRef.current = null; // turn ended without audio: don't count it
            setState(s);
          },
          onPartialTranscript: (text) => setTurns((t) => [...t, { role: "user", text }]),
          onToken: (text) =>
            setTurns((t) => {
              const last = t[t.length - 1];
              if (last?.role === "assistant") return [...t.slice(0, -1), { ...last, text: last.text + text }];
              return [...t, { role: "assistant", text }];
            }),
          onInterrupt: () => {
            playerRef.current?.stopAll();
            setInterruptTick((t) => t + 1);
          },
          // a turn failed server-side (session stays up): chime and show what the assistant is saying
          onServerError: (message) => {
            feedback("error");
            setTurns((t) => [...t, { role: "assistant", text: message }]);
          },
          onQuestion: setQuestion,
          // the server closes right after, once the goodbye has played: end cleanly, not as a drop
          onInterviewEnd: (id) => {
            feedback("end");
            closeSession(null);
            setInterviewId(id);
          },
          onAudioChunk: (chunk) => {
            if (thinkingAtRef.current !== null) {
              const ms = performance.now() - thinkingAtRef.current;
              thinkingAtRef.current = null;
              setLatency((l) => {
                const count = (l?.count ?? 0) + 1;
                return { last: ms, avg: ((l?.avg ?? 0) * (count - 1) + ms) / count, count };
              });
            }
            playerRef.current?.playChunk(chunk);
          },
          onClose: (code) => {
            // only an unexpected close lands here: hang-ups and failures null socketRef first, and a
            // stale socket closing after a new call started must not tear that call down
            if (socketRef.current !== socket) return;
            // an interview that was under way: try to pick it up again (the server waits for us)
            const retrying = interview && micRef.current;
            if (retrying && attempt < RECONNECT_DELAYS.length && !(code in CLOSE_ERRORS)) {
              playerRef.current?.stopAll();
              setReconnecting(true);
              setTimeout(() => {
                if (socketRef.current === socket) open(); // not hung up meanwhile
              }, RECONNECT_DELAYS[attempt++]);
              return;
            }
            closeSession(retrying ? "dropped" : (CLOSE_ERRORS[code] ?? (opened ? "dropped" : "unreachable")));
            feedback("error");
          },
          onError: () => {}, // always followed by onClose, which classifies the failure
        });

        socketRef.current = socket;
      };
      open();
    },
    [teardown, closeSession, onRecording],
  );

  const endCall = useCallback(() => {
    if (socketRef.current) feedback("end");
    closeSession(null);
  }, [closeSession]);

  // Tap-to-interrupt: cut playback locally right away, then tell the server to drop the turn.
  const interrupt = useCallback(() => {
    const socket = socketRef.current;
    if (socket?.readyState !== WebSocket.OPEN) return;
    playerRef.current?.stopAll();
    socket.send(JSON.stringify({ type: "interrupt" }));
    setInterruptTick((t) => t + 1);
    feedback("interrupt");
  }, []);

  // Disabling the track makes the mic source emit silence: the server's VAD just sees no speech,
  // the connection stays up, and the orb's mic level drops to zero.
  const toggleMute = useCallback(() => {
    const track = micRef.current?.stream.getAudioTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    setMuted(!track.enabled);
  }, []);

  return {
    state,
    turns,
    connecting,
    error,
    interruptTick,
    muted,
    reconnecting,
    latency,
    question,
    interviewId,
    connect,
    endCall,
    interrupt,
    toggleMute,
    getLevel,
    getMicLevel,
  };
}
