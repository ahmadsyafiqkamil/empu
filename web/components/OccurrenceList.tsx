"use client";

import { Play, Square } from "lucide-react";
import { useRef, useState } from "react";
import { formatTime } from "@/lib/time";
import { sourceLabel } from "@/lib/source";
import type { Occurrence } from "@/lib/types";

export function OccurrenceList({ occurrences }: { occurrences: Occurrence[] }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playingId, setPlayingId] = useState<number | null>(null);

  function play(o: Occurrence) {
    if (!o.audio_url) return;
    if (playingId === o.id) {
      audioRef.current?.pause();
      setPlayingId(null);
      return;
    }
    audioRef.current?.pause();
    const el = new Audio(o.audio_url);
    audioRef.current = el;
    el.onended = () => setPlayingId(null);
    setPlayingId(o.id);
    void el.play().catch(() => setPlayingId(null));
  }

  return (
    <ul className="flex flex-col border-t border-[var(--color-divider)]">
      {occurrences.map((o) => (
        <li
          key={o.id}
          className="grid grid-cols-[44px_minmax(0,1fr)] items-center gap-3 border-b border-[var(--color-divider)] py-3 lg:grid-cols-[36px_minmax(0,1fr)_auto_auto] lg:gap-3.5"
        >
          <button
            type="button"
            className="btn btn-secondary btn-icon"
            disabled={!o.audio_url}
            aria-label={`Play ${o.recording_title} at ${formatTime(o.t_start)}`}
            onClick={() => play(o)}
          >
            {playingId === o.id ? (
              <Square className="size-3.5" fill="currentColor" aria-hidden />
            ) : (
              <Play className="size-3.5" fill="currentColor" aria-hidden />
            )}
          </button>

          <span className="min-w-0 text-[14px] font-semibold lg:text-[15px]">{o.recording_title}</span>

          <span className="mono text-[12px] text-[var(--color-neutral-800)]">
            {formatTime(o.t_start)}
          </span>

          <span className="justify-self-end border border-current px-2 py-0.5 text-[11px] font-semibold">
            {sourceLabel(o.source)}
          </span>
        </li>
      ))}
    </ul>
  );
}
