export function ConnectButton({
  connected,
  disabled,
  onClick,
}: {
  connected: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="rounded-full px-6 py-3 text-base font-medium bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white transition-colors"
    >
      {connected ? "Listening…" : "Start talking"}
    </button>
  );
}
