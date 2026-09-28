import { useEffect, useRef, type ReactNode } from "react";
import { Icon } from "./CallControls";

// Bottom sheet on a native <dialog>: Esc-to-close, focus trap and backdrop come from the platform.
export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      // the content wrapper fills the dialog, so a click whose target is the dialog itself hit the backdrop
      onClick={(e) => e.target === ref.current && onClose()}
      aria-label={title}
      className="mt-auto mb-0 mx-auto w-full max-w-full sm:max-w-lg p-0 rounded-t-[20px] bg-surface text-ink shadow-ambient backdrop:bg-black/40 motion-safe:open:animate-slide-up"
    >
      <div className="flex flex-col max-h-[75dvh] font-sans">
        <header className="flex items-center justify-between px-5 py-4 border-b border-divider">
          <h2 className="text-[1.25rem] font-semibold text-ink">{title}</h2>
          <button
            onClick={onClose}
            aria-label={`Close ${title.toLowerCase()}`}
            className="size-9 rounded-full flex items-center justify-center text-ink-secondary hover:bg-divider/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
          >
            <Icon>
              <path d="M6 6l12 12M18 6L6 18" />
            </Icon>
          </button>
        </header>
        {children}
      </div>
    </dialog>
  );
}
