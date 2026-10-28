import { COPY } from "@/lib/copy";

export function NovelBadge() {
  return (
    <span
      title={COPY.novel.tooltip}
      className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--muted)]"
    >
      <span
        className="size-1.5 shrink-0 rounded-full bg-[var(--wax)]"
        aria-hidden
      />
      {COPY.novel.label}
    </span>
  );
}
