import { attributionLine, ensureTrimmedByEmpu } from "@/lib/copy";
import { cn } from "@/lib/cn";

export function AttributionLine({
  variant,
  attribution,
  title,
  creator,
  license,
  url,
}: {
  variant: "inline" | "card";
  attribution?: string | null;
  title?: string;
  creator?: string;
  license?: string;
  url?: string;
}) {
  const text = attribution
    ? ensureTrimmedByEmpu(attribution)
    : title && creator && license && url
      ? attributionLine({ title, creator, license, url })
      : null;
  if (!text) return null;
  return (
    <p
      className={cn(
        "text-xs text-[var(--muted)]",
        variant === "card" && "rounded-[var(--radius)] border border-[var(--line)] bg-[var(--surface)] p-3",
      )}
    >
      {text}
    </p>
  );
}
