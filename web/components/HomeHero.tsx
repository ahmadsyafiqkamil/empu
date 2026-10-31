"use client";

import Link from "next/link";
import { useState } from "react";
import { COPY } from "@/lib/copy";
import type { Archive, EntryListItem } from "@/lib/types";
import { ConfidenceTag } from "./ConfidenceTag";
import { SourceBadge } from "./SourceBadge";

export function HomeHero({
  archives,
  samples,
}: {
  archives: Archive[];
  samples: Record<string, EntryListItem | null>;
}) {
  const initial = archives.find((a) => a.is_demo) ?? archives[0] ?? null;
  const [slug, setSlug] = useState<string | null>(initial?.slug ?? null);

  const active = archives.find((a) => a.slug === slug) ?? null;
  const sample = slug ? (samples[slug] ?? null) : null;
  const still = sample?.keyframe_url ?? sample?.crop_url ?? null;

  return (
    <>
      {/* Hero */}
      <section className="grid grid-cols-1 border-b-2 border-[var(--color-divider)] lg:grid-cols-[7fr_5fr]">
        <div className="flex flex-col gap-6 border-b-2 border-[var(--color-divider)] px-5 pt-14 pb-10 lg:border-r-2 lg:border-b-0 lg:px-10 lg:pt-[72px] lg:pr-14 lg:pb-14">
          <h1 className="max-w-[16ch] text-[42px] leading-[0.95] tracking-[-0.035em] text-balance md:text-[64px] lg:text-[80px]">
            {COPY.tagline}
          </h1>
          <p className="max-w-[600px] text-[17px] leading-[1.5] text-pretty md:text-[18px]">
            {COPY.home.paragraph}
          </p>
          <div className="flex flex-wrap gap-2">
            {active ? (
              <Link
                href={`/d/${active.slug}`}
                className="btn btn-primary h-[52px] min-w-[220px] justify-start px-5 text-base"
              >
                {COPY.home.openArchive}
                <span className="ml-auto" aria-hidden>
                  →
                </span>
              </Link>
            ) : null}
            <Link href="/try" className="btn btn-secondary h-[52px] px-5 text-base">
              {COPY.home.tryClip}
            </Link>
            <Link href="/evidence" className="btn btn-ghost h-[52px] px-3 text-base text-[var(--color-text)] underline">
              {COPY.home.seeEvidence}
            </Link>
          </div>
        </div>

        <div className="flex flex-col">
          <div className="frame-media aspect-16/10">
            {still ? (
              // Frame URL only — original recording still, never generated.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={still} alt="" className="size-full object-cover" />
            ) : (
              <div className="grid size-full place-items-center px-6 text-center text-[13px] text-[var(--color-neutral-300)]">
                {active ? `${active.title} — no terms yet.` : COPY.empty.dictionary}
              </div>
            )}
          </div>
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-3 px-5 py-6 md:px-8">
            <div>
              <div className="label font-extrabold text-[var(--color-accent-700)]">
                {COPY.home.fromArchive}
              </div>
              <div className="font-heading mt-1 text-[28px] leading-tight tracking-[-0.02em] md:text-[32px]">
                {active?.title ?? "Empu"}
              </div>
              <div className="text-[13px] text-[var(--color-neutral-800)]">
                {sample?.gloss_en ?? active?.description ?? ""}
              </div>
            </div>
            {sample ? (
              <div className="flex flex-col items-end gap-1.5">
                <SourceBadge source={sample.source} size="sm" />
                {sample.confidence === "high" ||
                sample.confidence === "medium" ||
                sample.confidence === "low" ? (
                  <ConfidenceTag confidence={sample.confidence} ascii />
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      {/* Archives */}
      <section className="grid grid-cols-1 border-b-2 border-[var(--color-divider)] lg:grid-cols-[200px_repeat(3,minmax(0,1fr))]">
        <div className="label px-5 py-6 lg:px-10">{COPY.home.archives}</div>
        {archives.map((a) => {
          const on = a.slug === slug;
          return (
            <button
              key={a.slug}
              type="button"
              onClick={() => setSlug(a.slug)}
              aria-pressed={on}
              className={
                on
                  ? "flex flex-col gap-1.5 border-t border-[var(--color-divider)] px-5 py-5 text-left text-[var(--color-bg)] lg:border-t-0 lg:border-l lg:px-6 lg:py-6"
                  : "flex flex-col gap-1.5 border-t border-[var(--color-divider)] px-5 py-5 text-left text-[var(--color-text)] hover:bg-[var(--color-surface)] lg:border-t-0 lg:border-l lg:px-6 lg:py-6"
              }
              style={on ? { background: "var(--color-text)" } : undefined}
            >
              <span className="font-heading text-[19px] leading-tight lg:text-[20px]">
                {a.title}
              </span>
              <span className="text-[13px] opacity-85">
                {a.validated_count} terms · {a.recording_count} recordings
              </span>
            </button>
          );
        })}
        <div className="flex flex-col gap-1.5 border-t border-[var(--color-divider)] px-5 py-5 text-[var(--color-neutral-600)] lg:border-t-0 lg:border-l lg:px-6 lg:py-6">
          <span className="font-heading text-[19px] leading-tight lg:text-[20px]">Tenun</span>
          <span className="text-[13px]">{COPY.home.comingSoon}</span>
        </div>
      </section>
    </>
  );
}
