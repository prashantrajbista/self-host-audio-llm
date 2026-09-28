"use client";

import { Orb } from "@/components/Orb";
import { Transcript } from "@/components/Transcript";
import { ConnectButton } from "@/components/ConnectButton";
import { useVoiceSession } from "@/lib/useVoiceSession";

export default function Home() {
  const { state, transcript, connecting, error, interruptTick, connect } = useVoiceSession();
  const connected = state !== "disconnected";
  const orbState = connecting ? "connecting" : state;

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 bg-bg px-4 font-sans">
      <Orb state={orbState} interruptTick={interruptTick} />
      <div className="flex flex-col items-center gap-2">
        <ConnectButton
          connected={connected}
          connecting={connecting}
          disabled={connecting || connected}
          onClick={connect}
        />
        {!connected && !connecting && (
          <p className="text-ink-secondary text-xs">Uses your microphone — nothing is recorded or stored.</p>
        )}
        {connected && (
          <p className="text-ink-secondary text-xs">Full-duplex — talk anytime, even while it&apos;s replying.</p>
        )}
      </div>
      {error && <p className="text-error text-sm">{error}</p>}
      <Transcript text={transcript} />
    </main>
  );
}
