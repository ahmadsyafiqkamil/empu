import { COPY } from "@/lib/copy";

type Level = "high" | "medium" | "low";

const FILLED: Record<Level, number> = { high: 3, medium: 2, low: 1 };

export function ConfidenceTag({
  confidence,
  ascii = false,
}: {
  confidence: Level;
  /** Renders ●●●○○ instead of dots, for dense table cells. */
  ascii?: boolean;
}) {
  const filled = FILLED[confidence];
  return (
    <span className="inline-flex items-center gap-2 text-[13px]">
      <span className="inline-flex gap-1" aria-hidden>
        {ascii ? (
          <span className="tracking-[0.18em]">
            {"●".repeat(filled)}
            {"○".repeat(3 - filled)}
          </span>
        ) : (
          [0, 1, 2].map((i) => (
            <span
              key={i}
              className="size-1.5 rounded-full"
              style={{ background: i < filled ? "var(--color-text)" : "var(--color-neutral-400)" }}
            />
          ))
        )}
      </span>
      {COPY.confidence[confidence]}
    </span>
  );
}
