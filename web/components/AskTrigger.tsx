"use client";

import { openAsk } from "@/lib/askStore";

/**
 * Opens the shared Ask panel, optionally with a question already asked.
 *
 * `autoSend` sends it straight away (the entry page asks about the term being
 * read); without it the question is only prefilled.
 */
export function AskTrigger({
  question = "",
  autoSend = false,
  className = "btn btn-secondary",
  children,
}: {
  question?: string;
  autoSend?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      className={className}
      aria-haspopup="dialog"
      aria-controls="empu-ask-sheet"
      onClick={() => openAsk(question, { autoSend })}
    >
      {children}
    </button>
  );
}
