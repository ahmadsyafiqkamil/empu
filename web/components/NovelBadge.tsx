import { COPY } from "@/lib/copy";

export function NovelBadge() {
  return (
    <span
      title={COPY.novel.tooltip}
      className="inline-flex items-center text-xs font-medium"
      style={{ color: "var(--wax)" }}
    >
      {COPY.novel.label}
    </span>
  );
}
