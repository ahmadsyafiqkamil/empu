import { cn } from "@/lib/cn";
import type { EntryStatus } from "@/lib/types";

const LABELS: Record<EntryStatus, string> = {
  proposed: "Proposed",
  accepted: "Accepted",
  edited: "Edited",
  rejected: "Rejected",
  merged: "Merged",
};

export function StatusChip({ status }: { status: EntryStatus }) {
  const color =
    status === "accepted" || status === "edited"
      ? "var(--ok)"
      : status === "rejected"
        ? "var(--danger)"
        : "var(--muted)";
  return (
    <span
      className={cn("inline-flex items-center rounded-[var(--radius)] border px-1.5 py-0.5 text-xs")}
      style={{ color, borderColor: color }}
    >
      {LABELS[status]}
    </span>
  );
}
