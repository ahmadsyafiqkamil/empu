"use client";

import { useState } from "react";
import { EvidenceClip } from "./EvidenceClip";
import { SourceBadge } from "./SourceBadge";
import { StatusChip } from "./StatusChip";
import { COPY } from "@/lib/copy";
import { formatTime } from "@/lib/time";
import type { AskEvidence } from "@/lib/types";

function quoteText(evidence: AskEvidence): string | null {
  const { occurrence } = evidence;
  if (occurrence.evidence_quote) return occurrence.evidence_quote;
  if (occurrence.visible) return occurrence.visible;
  return null;
}

/**
 * One cited entry, with the evidence that backs it.
 *
 * The link target differs by surface: the public dictionary, or the studio
 * recording where a documenter can review the term in place.
 */
export function AskEvidenceCard({
  evidence,
  slug = "",
  studio = false,
}: {
  evidence: AskEvidence;
  slug?: string;
  studio?: boolean;
}) {
  const { entry, occurrence } = evidence;
  const [imageFailed, setImageFailed] = useState(false);
  const thumb = entry.crop_url ?? occurrence.keyframe_url ?? entry.keyframe_url ?? null;
  const quote = quoteText(evidence);
  const href = studio
    ? `/studio/recordings/${occurrence.recording_id}`
    : `/d/${slug}/${entry.id}`;

  return (
    <article className="flex flex-col gap-3 border-2 border-[var(--color-divider)] p-4">
      <header className="flex flex-wrap items-baseline gap-2">
        <h3 className="font-heading m-0 text-[24px] leading-none tracking-[-0.02em]">
          {entry.term}
        </h3>
        <span className="text-[12px] text-[var(--color-neutral-700)]">{entry.category}</span>
        {studio ? <StatusChip status={entry.status} /> : null}
      </header>

      <div className="grid grid-cols-[minmax(0,1fr)_104px] items-start gap-3">
        <EvidenceClip
          clipUrl={occurrence.clip_url}
          tStart={occurrence.t_start}
          tEnd={occurrence.t_end}
          source={occurrence.source}
          timeSource={occurrence.time_source}
        />
        <div className="frame-media grid aspect-4/5 place-items-center bg-[var(--color-surface)]">
          {thumb && !imageFailed ? (
            // Frame URL only — original recording stills, never generated images.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={thumb}
              alt={entry.term}
              className="size-full object-contain"
              onError={() => setImageFailed(true)}
            />
          ) : (
            <span className="p-2 text-center text-[11px] text-[var(--color-neutral-700)]">
              {COPY.crop.noCrop}
            </span>
          )}
        </div>
      </div>

      {quote ? (
        <blockquote className="m-0 border-l-2 border-[var(--color-accent)] pl-3 text-[15px] leading-snug">
          {occurrence.source === "visual_only" ? quote : `“${quote}”`}
          <footer className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-[var(--color-neutral-700)]">
            <span className="mono">{formatTime(occurrence.t_start)}</span>
            <span aria-hidden>·</span>
            <SourceBadge source={occurrence.source} size="sm" bordered={false} />
            {occurrence.recording_title ? (
              <>
                <span aria-hidden>·</span>
                <span>{occurrence.recording_title}</span>
              </>
            ) : null}
          </footer>
        </blockquote>
      ) : null}

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[13px]">
        <span>{entry.gloss_en}</span>
        <span className="text-[var(--color-neutral-700)]">{entry.gloss_id}</span>
      </div>

      <a href={href} className="btn btn-secondary self-start text-[13px]">
        {COPY.ask.openEntry} →
      </a>
    </article>
  );
}
