"use client";

import { Orb } from "@/components/Orb";
import { Transcript } from "@/components/Transcript";
import { ConnectButton } from "@/components/ConnectButton";
import { useVoiceSession } from "@/lib/useVoiceSession";

export default function Home() {
  const { state, transcript, connecting, error, connect } = useVoiceSession();
  const connected = state !== "disconnected";

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 bg-[#0b0f14] px-4">
      <Orb state={state} />
      <ConnectButton connected={connected} disabled={connecting || connected} onClick={connect} />
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <Transcript text={transcript} />
    </main>
  );
}
