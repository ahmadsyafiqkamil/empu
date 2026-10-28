import { AudioLines, Eye } from "lucide-react";
import { cn } from "@/lib/cn";
import { sourceColorVar, sourceLabel, sourceTooltip } from "@/lib/source";
import type { Source } from "@/lib/types";

function sourceIcon(source: Source, size: "sm" | "md") {
  const iconClass = size === "sm" ? "size-3" : "size-3.5";
  switch (source) {
    case "speech":
      return <AudioLines className={iconClass} aria-hidden />;
    case "on_screen_text":
      return (
        <span
          className={cn(
            "font-semibold leading-none",
            size === "sm" ? "text-xs" : "text-sm",
          )}
          aria-hidden
        >
          T
        </span>
      );
    case "visual_only":
      return <Eye className={iconClass} aria-hidden />;
    default: {
      const _exhaustive: never = source;
      return _exhaustive;
    }
  }
}

export function SourceBadge({
  source,
  size = "md",
}: {
  source: Source | null;
  size?: "sm" | "md";
}) {
  if (!source) return null;
  const color = sourceColorVar(source);
  const label = sourceLabel(source);
  return (
    <span
      title={sourceTooltip(source)}
      className={cn(
        "inline-flex items-center gap-1 font-medium",
        size === "sm" ? "text-xs" : "text-sm",
      )}
      style={{ color }}
    >
      {sourceIcon(source, size)}
      {label}
    </span>
  );
}
