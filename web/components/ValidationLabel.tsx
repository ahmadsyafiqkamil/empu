import { Check } from "lucide-react";
import { COPY, expertValidationLabel } from "@/lib/copy";

export function ValidationLabel({
  variant,
  expertName,
}: {
  variant: "documenter" | "expert" | "proposed";
  expertName?: string;
}) {
  const text =
    variant === "documenter"
      ? COPY.validation.documenter
      : variant === "proposed"
        ? COPY.validation.proposed
        : expertValidationLabel(expertName ?? "");
  return (
    <span className="inline-flex items-center gap-1 text-sm text-[var(--fg)]">
      {variant !== "proposed" ? <Check className="size-3.5 text-[var(--ok)]" aria-hidden /> : null}
      {text}
    </span>
  );
}
