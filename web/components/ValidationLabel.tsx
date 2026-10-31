import { Check } from "lucide-react";
import { COPY, expertValidationLabel } from "@/lib/copy";

export function ValidationLabel({
  variant,
  expertName,
}: {
  variant: "documenter" | "expert" | "proposed" | "rejected";
  expertName?: string;
}) {
  const text =
    variant === "documenter"
      ? COPY.validation.documenter
      : variant === "proposed"
        ? COPY.validation.proposed
        : variant === "rejected"
          ? "Rejected by the documenter"
          : expertValidationLabel(expertName ?? "");

  const positive = variant === "documenter" || variant === "expert";

  return (
    <span
      className="inline-flex items-center gap-2 text-[14px]"
      style={{ color: variant === "rejected" ? "var(--color-accent-700)" : undefined }}
    >
      {positive ? <Check className="size-4" aria-hidden /> : null}
      {text}
    </span>
  );
}
