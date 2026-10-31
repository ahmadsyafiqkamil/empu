import { AudioLines, Eye, Type } from "lucide-react";
import { sourceLabel, sourceTooltip } from "@/lib/source";
import type { Source } from "@/lib/types";

function SourceIcon({ source, size }: { source: Source; size: "sm" | "md" }) {
  const cls = size === "sm" ? "size-3" : "size-3.5";
  switch (source) {
    case "speech":
      return <AudioLines className={cls} aria-hidden />;
    case "on_screen_text":
      return <Type className={cls} aria-hidden />;
    case "visual_only":
      return <Eye className={cls} aria-hidden />;
    default: {
      const _exhaustive: never = source;
      return _exhaustive;
    }
  }
}

/** Icon plus label, never colour alone. Outlined so it reads on any ground. */
export function SourceBadge({
  source,
  size = "md",
  bordered = true,
}: {
  source: Source | null;
  size?: "sm" | "md";
  bordered?: boolean;
}) {
  if (!source) return null;
  return (
    <span
      title={sourceTooltip(source)}
      className={
        bordered
          ? "inline-flex items-center gap-1.5 border border-current px-1.5 py-0.5 font-semibold whitespace-nowrap"
          : "inline-flex items-center gap-1.5 font-semibold whitespace-nowrap"
      }
      style={{ fontSize: size === "sm" ? 11 : 12 }}
    >
      <SourceIcon source={source} size={size} />
      {sourceLabel(source)}
    </span>
  );
}
