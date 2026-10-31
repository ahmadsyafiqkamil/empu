"use client";

import { useState } from "react";
import { COPY } from "@/lib/copy";
import { TimeSourceTag } from "./TimeSourceTag";
import { formatTimeRange } from "@/lib/time";
import { SourceBadge } from "./SourceBadge";
import type { Source } from "@/lib/types";

export function EvidenceClip({
  clipUrl,
  tStart,
  tEnd,
  source,
  timeSource,
}: {
  clipUrl: string | null;
  tStart: number;
  tEnd: number;
  source: Source;
  timeSource: "asr" | "muse";
}) {
  const [error, setError] = useState(false);

  return (
    <figure className="flex flex-col gap-2">
      <div className="frame-media aspect-video">
        {clipUrl && !error ? (
          <video
            className="size-full object-contain"
            controls
            playsInline
            preload="metadata"
            src={clipUrl}
            onError={() => setError(true)}
          />
        ) : (
          <div className="grid size-full place-items-center bg-[var(--color-surface)] text-[13px] text-[var(--color-neutral-700)]">
            {COPY.empty.clip}
          </div>
        )}
      </div>
      <figcaption className="flex flex-wrap items-center gap-2.5 text-[12px] text-[var(--color-neutral-800)]">
        <span className="mono">{formatTimeRange(tStart, tEnd)}</span>
        <span aria-hidden>·</span>
        <SourceBadge source={source} />
        <span aria-hidden>·</span>
        <TimeSourceTag timeSource={timeSource} />
      </figcaption>
    </figure>
  );
}
