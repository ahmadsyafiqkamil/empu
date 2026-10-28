import { COPY } from "@/lib/copy";

type Level = "high" | "medium" | "low";

const FILLED: Record<Level, number> = { high: 3, medium: 2, low: 1 };

export function ConfidenceTag({ confidence }: { confidence: Level }) {
  const filled = FILLED[confidence];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-[var(--muted)]">
      <span className="inline-flex gap-0.5" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 rounded-full"
            style={{ background: i < filled ? "var(--fg)" : "var(--line)" }}
          />
        ))}
      </span>
      {COPY.confidence[confidence]}
    </span>
  );
}
