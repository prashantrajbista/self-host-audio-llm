export type OrbState = "idle" | "listening" | "thinking" | "speaking";

type ServerMessage =
  | { type: "state"; data: OrbState }
  | { type: "partial_transcript"; data: string }
  | { type: "token"; data: string }
  | { type: "interrupt"; data: null }
  | { type: "error"; data: string };

export interface VoiceSocketHandlers {
  onState: (state: OrbState) => void;
  onPartialTranscript: (text: string) => void;
  onToken: (text: string) => void;
  onInterrupt: () => void;
  onServerError: (message: string) => void;
  onAudioChunk: (chunk: ArrayBuffer) => void;
  onOpen: () => void;
  onClose: () => void;
  onError: () => void;
}

export function connectVoiceSocket(
  url: string,
  handlers: VoiceSocketHandlers,
): WebSocket {
  const socket = new WebSocket(url);
  socket.binaryType = "arraybuffer";

  socket.onopen = () => handlers.onOpen();
  socket.onclose = () => handlers.onClose();
  socket.onerror = () => handlers.onError();

  socket.onmessage = (event: MessageEvent) => {
    if (typeof event.data === "string") {
      const msg = JSON.parse(event.data) as ServerMessage;
      if (msg.type === "state") handlers.onState(msg.data);
      if (msg.type === "partial_transcript") handlers.onPartialTranscript(msg.data);
      if (msg.type === "token") handlers.onToken(msg.data);
      if (msg.type === "interrupt") handlers.onInterrupt();
      if (msg.type === "error") handlers.onServerError(msg.data);
    } else {
      handlers.onAudioChunk(event.data as ArrayBuffer);
    }
  };

  return socket;
}

export function gatewayWsUrl(voice?: string): string {
  const url = new URL(baseWsUrl());
  if (voice) url.searchParams.set("voice", voice);
  return url.toString();
}

// HTTP origin of the same gateway (voice previews), derived from the WS URL.
export function gatewayHttpUrl(path: string): string {
  const url = new URL(baseWsUrl());
  url.protocol = url.protocol === "wss:" ? "https:" : "http:";
  url.pathname = path;
  url.search = "";
  return url.toString();
}

function baseWsUrl(): string {
  const configured = process.env.NEXT_PUBLIC_GATEWAY_WS_URL;
  if (configured) return configured;
  const protocol =
    typeof window !== "undefined" && window.location.protocol === "https:"
      ? "wss:"
      : "ws:";
  const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `${protocol}//${host}:8000/ws`;
}
