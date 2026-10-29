import Link from "next/link";
import { AttributionLine } from "@/components/AttributionLine";
import { ConfidenceTag } from "@/components/ConfidenceTag";
import { CropView } from "@/components/CropView";
import { EvidenceClip } from "@/components/EvidenceClip";
import { NovelBadge } from "@/components/NovelBadge";
import { PronounceButton } from "@/components/PronounceButton";
import { SourceBadge } from "@/components/SourceBadge";
import {
  CATEGORY_LABEL,
  COPY,
  alsoHeardAs,
  heardInRecordings,
  shownOnScreenAt,
  saidAt,
} from "@/lib/copy";
import { formatTime } from "@/lib/time";
import type { Entry, Source } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

function quoteCaption(source: Source, t: number): string {
  return source === "on_screen_text" ? shownOnScreenAt(formatTime(t)) : saidAt(formatTime(t));
}

export default async function EntryPage({
  params,
}: {
  params: Promise<{ slug: string; id: string }>;
}) {
  const { slug, id } = await params;
  const r = await fetch(`${API}/api/public/entries/${id}`, { cache: "no-store" });
  if (!r.ok) {
    return <p className="p-8">{COPY.empty.entry404}</p>;
  }
  const e: Entry = await r.json();
  const occ = e.best_occurrence;
  const source: Source | null = e.source ?? occ?.source ?? null;
  const conf = occ?.confidence;

  return (
    <article className="mx-auto grid max-w-5xl gap-8 p-6 lg:grid-cols-2">
      {/* Evidence column first */}
      <div className="space-y-4">
        <p className="text-sm text-[var(--muted)]">
          <Link href={`/d/${slug}`} className="underline">
            Living Archive · Batik Tulis
          </Link>
        </p>
        {occ ? (
          <EvidenceClip
            clipUrl={e.clip_url}
            tStart={occ.t_start}
            tEnd={occ.t_end}
            source={occ.source}
            timeSource={occ.time_source}
          />
        ) : null}
        <CropView
          cropUrl={e.crop_url}
          overlayUrl={e.overlay_url}
          keyframeUrl={e.keyframe_url}
          samStatus={e.sam_status}
        />
      </div>

      {/* Meaning column */}
      <div className="space-y-3">
        <h1 className="flex items-center gap-2 font-display text-4xl">
          {e.term}
          <PronounceButton audioUrl={occ?.audio_url ?? null} />
        </h1>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {e.category ? (
            <span className="border border-[var(--line)] px-2 py-0.5 text-xs">
              {CATEGORY_LABEL[e.category] ?? e.category}
            </span>
          ) : null}
          {e.stage_id ? (
            <span className="border border-[var(--line)] px-2 py-0.5 text-xs">{e.stage_id}</span>
          ) : null}
          {e.is_novel ? <NovelBadge /> : null}
        </div>
        {e.variants && e.variants.length > 0 ? (
          <p className="text-sm">
            {alsoHeardAs(e.variants.join(", "))}
          </p>
        ) : null}
        {occ?.evidence_quote ? (
          <blockquote className="border-l-2 border-[var(--accent)] pl-3 text-sm">
            <p>{occ.evidence_quote}</p>
            <p className="mt-1 text-xs text-[var(--muted)]">{quoteCaption(source ?? "speech", occ.t_start)}</p>
          </blockquote>
        ) : null}
        <div>
          <p className="font-display text-xl">{e.gloss_en}</p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            <span className="block text-xs">Bahasa Indonesia</span>
            {e.gloss_id}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {source ? <SourceBadge source={source} /> : null}
          {conf ? <ConfidenceTag confidence={conf} /> : null}
        </div>
        <p className="text-sm">
          {e.validation_label ?? COPY.validation.documenter}
        </p>
        {e.attribution ? <AttributionLine variant="card" attribution={e.attribution} /> : null}
        <p className="text-sm text-[var(--muted)]">{heardInRecordings(e.occurrences?.length ?? 0)}</p>
        {occ ? (
          <p className="text-sm">
            <Link href={`/d/${slug}/map/${occ.recording_id}`} className="underline">
              Process map
            </Link>
          </p>
        ) : null}
      </div>
    </article>
  );
}