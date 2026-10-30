"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/cn";
import { COPY } from "@/lib/copy";
import type { Archive, EntryListItem } from "@/lib/types";
import { ConfidenceTag } from "./ConfidenceTag";
import { SourceBadge } from "./SourceBadge";

export function ArchivePicker({ archives }: { archives: Archive[] }) {
  const initial =
    archives.find((a) => a.is_demo) ?? archives[0] ?? null;
  const [slug, setSlug] = useState<string | null>(initial?.slug ?? null);
  const [entries, setEntries] = useState<EntryListItem[]>([]);

  useEffect(() => {
    if (!slug) {
      setEntries([]);
      return;
    }
    let cancelled = false;
    apiGet<EntryListItem[]>(`/api/public/archives/${slug}/entries`)
      .then((list) => {
        if (!cancelled) setEntries(list);
      })
      .catch(() => {
        if (!cancelled) setEntries([]);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const active = archives.find((a) => a.slug === slug) ?? null;
  const sample = entries.find((e) => e.keyframe_url || e.crop_url) ?? entries[0] ?? null;

  return (
    <section>
      <p className="font-display text-3xl">
        empu<span className="text-[var(--wax)]">.</span>
      </p>
      <h1 className="mt-4 max-w-xl font-display text-4xl leading-tight">{COPY.tagline}</h1>
      <p className="mt-5 max-w-xl text-[var(--muted)]">{COPY.home.paragraph}</p>

      {/* Archive chips — one per public archive, grows as packs are added */}
      <nav className="mt-6 flex flex-wrap gap-2" aria-label="Archives">
        {archives.map((a) => (
          <button
            key={a.slug}
            type="button"
            onClick={() => setSlug(a.slug)}
            className={cn(
              "border px-3 py-1.5 text-sm",
              a.slug === slug
                ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                : "border-[var(--line)] bg-transparent",
            )}
          >
            {a.title}
            <span className={cn("ml-2 text-xs", a.slug === slug ? "text-white/80" : "text-[var(--muted)]")}>
              {a.validated_count}
            </span>
          </button>
        ))}
      </nav>

      <div className="mt-7 flex flex-wrap gap-3">
        {slug ? (
          <Link href={`/d/${slug}`} className="bg-[var(--accent)] px-4 py-2 text-white">
            {COPY.home.openArchive}
          </Link>
        ) : null}
        <Link href="/try" className="border border-[var(--line)] px-4 py-2">
          {COPY.home.tryClip}
        </Link>
        <Link href="/evidence" className="border border-[var(--line)] px-4 py-2">
          {COPY.home.seeEvidence}
        </Link>
      </div>

      {/* Dynamic feature card for the selected archive */}
      <div className="mt-10 grid gap-6 md:grid-cols-2 md:items-start">
        <div className="aspect-video overflow-hidden bg-[var(--surface)]">
          {sample?.keyframe_url || sample?.crop_url ? (
            // Frame URL only — original recording still, never generated.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={sample.keyframe_url ?? sample.crop_url ?? undefined}
              alt={sample.term}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center p-6 text-center text-sm text-[var(--muted)]">
              {active ? `${active.title} — no terms yet.` : COPY.empty.dictionary}
            </div>
          )}
        </div>
        <div className="flex flex-col gap-3 border border-[var(--line)] bg-[var(--surface)] p-4">
          {sample ? (
            <>
              <p className="font-display text-2xl">{sample.term}</p>
              <div className="flex flex-wrap items-center gap-3">
                <SourceBadge source={sample.source} />
                {sample.confidence ? (
                  <ConfidenceTag
                    confidence={
                      sample.confidence === "high" ||
                      sample.confidence === "medium" ||
                      sample.confidence === "low"
                        ? sample.confidence
                        : "medium"
                    }
                  />
                ) : null}
              </div>
            </>
          ) : (
            <>
              <p className="font-display text-2xl">{active?.title ?? "Archive"}</p>
              <p className="text-sm text-[var(--muted)]">
                {active ? `${active.recording_count} recordings` : "No archive selected"}
              </p>
            </>
          )}
        </div>
      </div>
    </section>
  );
}