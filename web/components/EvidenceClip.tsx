"use client";

import { useState } from "react";
import { COPY } from "@/lib/copy";
import { sourceLabel, timeSourceLabel } from "@/lib/source";
import { formatTimeRange } from "@/lib/time";
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
  const caption = `${formatTimeRange(tStart, tEnd)} · ${sourceLabel(source)} · ${timeSourceLabel(timeSource)}`;
  if (!clipUrl || error) {
    return (
      <figure className="space-y-1">
        <div className="flex aspect-video items-center justify-center bg-[var(--surface)] text-sm text-[var(--muted)]">
          {COPY.empty.clip}
        </div>
        <figcaption className="font-mono text-xs text-[var(--muted)]">{caption}</figcaption>
      </figure>
    );
  }
  return (
    <figure className="space-y-1">
      <video
        className="aspect-video w-full bg-[var(--surface)] object-contain"
        controls
        preload="metadata"
        src={clipUrl}
        onError={() => setError(true)}
      />
      <figcaption className="font-mono text-xs text-[var(--muted)]">{caption}</figcaption>
    </figure>
  );
}
