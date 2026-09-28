"use client";

import { useCallback, useRef, useState } from "react";
import { connectVoiceSocket, gatewayWsUrl, type OrbState } from "./ws";
import { Player, audioLevel, startMic } from "./audio";

export type SessionState = OrbState | "disconnected";

export function useVoiceSession() {
  const [state, setState] = useState<SessionState>("disconnected");
  const [transcript, setTranscript] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interruptTick, setInterruptTick] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const playerRef = useRef<Player | null>(null);
  const micAnalyserRef = useRef<AnalyserNode | null>(null);

  // Louder of mic and playback, 0..1 — polled per animation frame by the orb, not React state.
  const getLevel = useCallback(
    () => Math.max(audioLevel(micAnalyserRef.current), audioLevel(playerRef.current?.analyser ?? null)),
    [],
  );

  const connect = useCallback(() => {
    setError(null);
    setConnecting(true);
    const player = new Player(24000);
    playerRef.current = player;

    const socket = connectVoiceSocket(gatewayWsUrl(), {
      onOpen: async () => {
        try {
          const mic = await startMic((pcm16) => {
            if (socket.readyState === WebSocket.OPEN) socket.send(pcm16);
          });
          micAnalyserRef.current = mic.analyser;
          setState("idle");
          setConnecting(false);
        } catch {
          setError("Microphone access denied.");
          setConnecting(false);
          socket.close();
        }
      },
      onState: (s) => setState(s),
      onPartialTranscript: (text) => setTranscript(text),
      onToken: (text) => setTranscript((prev) => prev + text),
      onInterrupt: () => {
        playerRef.current?.stopAll();
        setInterruptTick((t) => t + 1);
      },
      onAudioChunk: (chunk) => playerRef.current?.playChunk(chunk),
      onClose: () => {
        setState("disconnected");
        setConnecting(false);
        socketRef.current = null;
        micAnalyserRef.current = null;
      },
      onError: () => {
        setError("Connection lost.");
        setState("disconnected");
        setConnecting(false);
      },
    });

    socketRef.current = socket;
  }, []);

  return { state, transcript, connecting, error, interruptTick, connect, getLevel };
}
