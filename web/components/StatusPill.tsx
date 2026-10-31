import type { EntryStatus } from "@/lib/types";

const LABELS: Record<EntryStatus, string> = {
  proposed: "Proposed",
  accepted: "Accepted",
  edited: "Edited",
  rejected: "Rejected",
  merged: "Merged",
};

/** Filled = settled, outlined = still open. Never colour alone. */
export function StatusPill({ status }: { status: EntryStatus }) {
  const style: React.CSSProperties = (() => {
    switch (status) {
      case "accepted":
        return { background: "var(--color-text)", color: "var(--color-bg)", borderColor: "var(--color-text)" };
      case "edited":
        return { background: "var(--color-neutral-300)", color: "var(--color-neutral-900)", borderColor: "var(--color-neutral-300)" };
      case "rejected":
        return { background: "var(--color-accent-100)", color: "var(--color-accent-800)", borderColor: "var(--color-accent-300)" };
      case "merged":
        return { background: "transparent", color: "var(--color-neutral-600)", borderColor: "var(--color-neutral-500)" };
      case "proposed":
      default:
        return { background: "transparent", color: "var(--color-text)", borderColor: "var(--color-neutral-500)" };
    }
  })();

  return (
    <span
      className="inline-flex items-center border px-1.5 py-0.5 text-[11px] font-semibold whitespace-nowrap"
      style={style}
    >
      {LABELS[status]}
    </span>
  );
}
