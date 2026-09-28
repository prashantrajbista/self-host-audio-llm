export function ConnectButton({
  connected,
  connecting,
  disabled,
  onClick,
}: {
  connected: boolean;
  connecting: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const label = connecting ? "Connecting…" : connected ? "Listening…" : "Start talking";

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="rounded-full px-7 py-3 text-[0.9375rem] font-semibold bg-primary hover:bg-primary-hover disabled:bg-divider disabled:text-ink-secondary disabled:cursor-not-allowed text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
    >
      {label}
    </button>
  );
}
