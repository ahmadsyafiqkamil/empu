import { COPY } from "@/lib/copy";

export function NovelBadge({ compact = false }: { compact?: boolean }) {
  return (
    <span
      title={COPY.novel.tooltip}
      className="tag tag-accent font-semibold"
      style={compact ? { padding: "2px 6px" } : { padding: "3px 8px" }}
    >
      {COPY.novel.label}
    </span>
  );
}
