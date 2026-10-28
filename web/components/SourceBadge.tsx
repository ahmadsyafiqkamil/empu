import { AudioLines, Eye } from "lucide-react";
import { cn } from "@/lib/cn";
import { sourceColorVar, sourceLabel, sourceTooltip } from "@/lib/source";
import type { Source } from "@/lib/types";

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
  const iconClass = size === "sm" ? "size-3" : "size-3.5";
  return (
    <span
      title={sourceTooltip(source)}
      className={cn(
        "inline-flex items-center gap-1 font-medium",
        size === "sm" ? "text-xs" : "text-sm",
      )}
      style={{ color }}
    >
      {source === "speech" ? (
        <AudioLines className={iconClass} aria-hidden />
      ) : source === "on_screen_text" ? (
        <span className={cn("font-semibold leading-none", size === "sm" ? "text-xs" : "text-sm")} aria-hidden>
          T
        </span>
      ) : (
        <Eye className={iconClass} aria-hidden />
      )}
      {label}
    </span>
  );
}
