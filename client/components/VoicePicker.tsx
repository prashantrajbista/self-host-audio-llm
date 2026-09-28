import { useEffect, useRef, useState } from "react";
import { Orb } from "./Orb";
import { Icon } from "./CallControls";
import { Sheet } from "./Sheet";
import { gatewayHttpUrl } from "@/lib/ws";
import { VOICES, type Voice } from "@/lib/voices";

export function VoicePicker({
  open,
  onClose,
  selected,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  selected: Voice;
  onSelect: (voice: Voice) => void;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);

  const stop = () => {
    audioRef.current?.pause();
    audioRef.current = null;
    setPlaying(null);
  };

  useEffect(() => {
    if (!open) stop();
  }, [open]);

  const preview = (voice: Voice) => {
    const wasPlaying = playing === voice.id;
    stop();
    if (wasPlaying) return;
    setFailed(null);
    const audio = new Audio(gatewayHttpUrl(`/voices/${voice.id}/preview`));
    audioRef.current = audio;
    setPlaying(voice.id);
    audio.onended = () => setPlaying((p) => (p === voice.id ? null : p));
    audio.play().catch(() => {
      setPlaying(null);
      setFailed(voice.id);
    });
  };

  return (
    <Sheet open={open} onClose={onClose} title="Choose a voice">
      {/* rendered only while open: each row's orb runs its own animation loop */}
      {open && (
        <ul className="overflow-y-auto py-2">
          {VOICES.map((voice) => {
            const isSelected = voice.id === selected.id;
            return (
              <li key={voice.id} className="flex items-center gap-3 px-5 py-2">
                <button
                  onClick={() => onSelect(voice)}
                  aria-pressed={isSelected}
                  className="flex-1 flex items-center gap-4 rounded-[12px] p-2 -m-2 text-left hover:bg-divider/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
                >
                  <Orb state="idle" size={56} palette={voice.palette} />
                  <span className="flex-1">
                    <span className="block font-semibold text-ink">
                      {voice.name}
                    </span>
                    <span className="block text-sm text-ink-secondary">
                      {failed === voice.id
                        ? "Preview unavailable — is the gateway running?"
                        : voice.description}
                    </span>
                  </span>
                  {isSelected && (
                    <span className="text-primary">
                      <Icon>
                        <path d="M5 12l5 5L19 7" />
                      </Icon>
                    </span>
                  )}
                </button>
                <button
                  onClick={() => preview(voice)}
                  aria-label={
                    playing === voice.id
                      ? `Stop ${voice.name} preview`
                      : `Preview ${voice.name}`
                  }
                  className="size-10 shrink-0 rounded-full flex items-center justify-center border border-divider text-ink hover:bg-divider/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
                >
                  <Icon>
                    {playing === voice.id ? (
                      <path d="M8 6h3v12H8zM13 6h3v12h-3z" />
                    ) : (
                      <path d="M8 5l11 7-11 7z" />
                    )}
                  </Icon>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Sheet>
  );
}
