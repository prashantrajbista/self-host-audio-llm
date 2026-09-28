"use client";

import { useCallback, useRef, useState } from "react";
import { connectVoiceSocket, gatewayWsUrl, type OrbState } from "./ws";
import { Player, audioLevel, startMic } from "./audio";

export type SessionState = OrbState | "disconnected";

export interface Turn {
  role: "user" | "assistant";
  text: string;
}

type Mic = Awaited<ReturnType<typeof startMic>>;

export function useVoiceSession() {
  const [state, setState] = useState<SessionState>("disconnected");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interruptTick, setInterruptTick] = useState(0);
  const [muted, setMuted] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const playerRef = useRef<Player | null>(null);
  const micRef = useRef<Mic | null>(null);

  // Louder of mic and playback, 0..1 — polled per animation frame by the orb, not React state.
  const getLevel = useCallback(
    () => Math.max(audioLevel(micRef.current?.analyser ?? null), audioLevel(playerRef.current?.analyser ?? null)),
    [],
  );

  // Release mic + audio output. Shared by user hang-up and dropped connections, so the mic never
  // stays live after a call ends. Idempotent: refs are nulled as they're released.
  const teardown = useCallback(() => {
    const mic = micRef.current;
    micRef.current = null;
    mic?.stream.getTracks().forEach((t) => t.stop());
    void mic?.ctx.close();
    playerRef.current?.close();
    playerRef.current = null;
    setMuted(false);
  }, []);

  const connect = useCallback(() => {
    setError(null);
    setTurns([]);
    setConnecting(true);
    const player = new Player(24000);
    playerRef.current = player;

    const socket = connectVoiceSocket(gatewayWsUrl(), {
      onOpen: async () => {
        try {
          const mic = await startMic((pcm16) => {
            if (socket.readyState === WebSocket.OPEN) socket.send(pcm16);
          });
          // call ended while the permission prompt was open: release the mic we just got
          if (socketRef.current !== socket) {
            mic.stream.getTracks().forEach((t) => t.stop());
            void mic.ctx.close();
            return;
          }
          micRef.current = mic;
          setState("idle");
          setConnecting(false);
        } catch {
          setError("Microphone access denied.");
          socket.close();
        }
      },
      onState: (s) => setState(s),
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
      onAudioChunk: (chunk) => playerRef.current?.playChunk(chunk),
      onClose: () => {
        // a stale socket closing (user hung up, then started a new call) must not tear down the new one
        if (socketRef.current !== socket) return;
        socketRef.current = null;
        teardown();
        setState("disconnected");
        setConnecting(false);
      },
      onError: () => {
        if (socketRef.current === socket) setError("Connection lost.");
      },
    });

    socketRef.current = socket;
  }, [teardown]);

  const endCall = useCallback(() => {
    const socket = socketRef.current;
    socketRef.current = null;
    socket?.close();
    teardown();
    setState("disconnected");
    setConnecting(false);
  }, [teardown]);

  // Disabling the track makes the mic source emit silence: the server's VAD just sees no speech,
  // the connection stays up, and the orb's mic level drops to zero.
  const toggleMute = useCallback(() => {
    const track = micRef.current?.stream.getAudioTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    setMuted(!track.enabled);
  }, []);

  return { state, turns, connecting, error, interruptTick, muted, connect, endCall, toggleMute, getLevel };
}
