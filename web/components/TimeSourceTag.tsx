import { timeSourceLabel, timeSourceTooltip } from "@/lib/source";

export function TimeSourceTag({ timeSource }: { timeSource: "asr" | "muse" }) {
  return (
    <span title={timeSourceTooltip(timeSource)} className="text-xs text-[var(--muted)]">
      {timeSourceLabel(timeSource)}
    </span>
  );
}
