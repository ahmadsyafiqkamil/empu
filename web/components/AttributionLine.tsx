import { attributionLine, ensureTrimmedByEmpu } from "@/lib/copy";

export function AttributionLine({
  attribution,
  title,
  creator,
  license,
  url,
}: {
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
  return <p className="text-[13px] leading-relaxed text-[var(--color-neutral-700)]">{text}</p>;
}

/** The boxed source block used on the entry page and in the studio. */
export function SourceCard({
  title,
  attribution,
  contributor,
  note,
}: {
  title?: string | null;
  attribution?: string | null;
  contributor?: string | null;
  note?: string | null;
}) {
  const text = attribution ? ensureTrimmedByEmpu(attribution) : null;
  if (!title && !text && !contributor) return null;
  return (
    <div className="flex flex-col gap-1 bg-[var(--color-surface)] p-4 text-[13px]">
      <span className="label">Source</span>
      {title ? <span className="font-semibold text-[var(--color-text)]">{title}</span> : null}
      {contributor ? (
        <span className="text-[var(--color-neutral-800)]">Recorded by {contributor}</span>
      ) : null}
      {text ? <span className="text-[var(--color-neutral-800)]">{text}</span> : null}
      {note ? <span className="text-[var(--color-neutral-800)]">{note}</span> : null}
    </div>
  );
}
