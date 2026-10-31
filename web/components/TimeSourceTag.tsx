import { timeSourceLabel, timeSourceTooltip } from "@/lib/source";

export function TimeSourceTag({ timeSource }: { timeSource: "asr" | "muse" }) {
  return (
    <span title={timeSourceTooltip(timeSource)} className="text-[11px] text-[var(--color-neutral-700)]">
      {timeSourceLabel(timeSource)}
    </span>
  );
}
