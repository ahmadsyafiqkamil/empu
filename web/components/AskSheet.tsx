"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { COPY } from "@/lib/copy";

/**
 * A native <dialog> in modal mode: Esc, focus trapping and `inert` on the page
 * behind all come from the platform. `showModal()` also moves focus inside, so
 * the caller's autofocus target wins.
 */
export function AskSheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const previous = document.documentElement.style.overflow;
    document.documentElement.style.overflow = "hidden";
    return () => {
      document.documentElement.style.overflow = previous;
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      id="empu-ask-sheet"
      className="ask-sheet"
      aria-labelledby="empu-ask-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClose={onClose}
    >
      <header className="flex items-center gap-3 border-b-2 border-[var(--color-divider)] px-5 py-4">
        <h2
          id="empu-ask-title"
          className="font-heading m-0 mr-auto text-[20px] leading-none tracking-[-0.02em]"
        >
          {title}
        </h2>
        <button
          type="button"
          className="btn btn-secondary btn-icon"
          aria-label={COPY.ask.close}
          onClick={onClose}
        >
          <X className="size-4" aria-hidden />
        </button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">{children}</div>
    </dialog>
  );
}
