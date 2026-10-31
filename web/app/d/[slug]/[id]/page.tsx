import Link from "next/link";
import { SourceCard } from "@/components/AttributionLine";
import { ConfidenceTag } from "@/components/ConfidenceTag";
import { CropView } from "@/components/CropView";
import { EvidenceClip } from "@/components/EvidenceClip";
import { NovelBadge } from "@/components/NovelBadge";
import { OccurrenceList } from "@/components/OccurrenceList";
import { PronounceButton } from "@/components/PronounceButton";
import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { SourceBadge } from "@/components/SourceBadge";
import { ValidationLabel } from "@/components/ValidationLabel";
import { CATEGORY_LABEL, COPY } from "@/lib/copy";
import { formatTime } from "@/lib/time";
import type { Archive, Entry, Source } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

type Pack = {
  id: string;
  stages: { id: string; label: { id: string; en: string } }[];
};

function quoteLabel(source: Source, t: number): string {
  const time = formatTime(t);
  switch (source) {
    case "speech":
      return `Said at ${time}`;
    case "on_screen_text":
      return `Shown on screen at ${time}`;
    case "visual_only":
      return `Seen at ${time}`;
    default:
      return `At ${time}`;
  }
}

function QuoteBody({ source, text }: { source: Source; text: string }) {
  if (source === "visual_only") return <>Not spoken or written; seen in the video.</>;
  if (source === "on_screen_text") return <>{text}</>;
  return <>“{text}”</>;
}

export default async function EntryPage({
  params,
}: {
  params: Promise<{ slug: string; id: string }>;
}) {
  const { slug, id } = await params;

  const archive: Archive | null = await fetch(`${API}/api/public/archives/${slug}`, {
    cache: "no-store",
  })
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);

  const r = await fetch(`${API}/api/public/entries/${id}`, { cache: "no-store" });
  if (!r.ok) {
    return (
      <>
        <PublicHeader />
        <main className="mx-auto w-full max-w-[1100px] px-5 py-16 lg:px-0">
          <div className="empty">
            <span>{COPY.empty.entry404}</span>
            {archive ? (
              <Link href={`/d/${archive.slug}`} className="btn btn-secondary">
                Back to the dictionary
              </Link>
            ) : null}
          </div>
        </main>
        <PublicFooter />
      </>
    );
  }

  const e: Entry = await r.json();
  const occ = e.best_occurrence;
  const source: Source = e.source ?? occ?.source ?? "speech";
  const conf = e.confidence ?? occ?.confidence ?? null;

  const pack: Pack | null = archive
    ? await fetch(`${API}/api/packs/${archive.craft_pack_id}`, { cache: "no-store" })
        .then((res) => (res.ok ? res.json() : null))
        .catch(() => null)
    : null;

  const stageLabel = pack?.stages?.find((s) => s.id === e.stage_id)?.label?.en;
  const categoryLabel = CATEGORY_LABEL[e.category] ?? e.category;

  return (
    <>
      <PublicHeader />
      <main className="mx-auto w-full max-w-[1100px] px-5 pt-7 pb-16 lg:px-0 lg:pt-8">
        <p className="flex flex-wrap gap-2 text-[13px] text-[var(--color-neutral-700)]">
          <Link href={`/d/${slug}`} className="text-inherit">
            {archive?.title ?? slug}
          </Link>
          <span aria-hidden>/</span>
          <span>{categoryLabel}</span>
        </p>

        {/* Headword */}
        <div className="grid grid-cols-[minmax(0,1fr)] items-end gap-4 border-b-2 border-[var(--color-divider)] py-6 lg:grid-cols-[minmax(0,1fr)_auto]">
          <div>
            <h1 className="text-[44px] leading-[0.95] tracking-[-0.03em] md:text-[58px] lg:text-[76px]">
              {e.term}
            </h1>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="border border-[var(--color-divider)] px-2.5 py-1 text-[13px] font-semibold">
                {categoryLabel}
              </span>
              {e.stage_id ? (
                <span className="border border-[var(--color-divider)] px-2.5 py-1 text-[13px]">
                  {e.stage_id}
                  {stageLabel ? ` · ${stageLabel}` : ""}
                </span>
              ) : null}
              {e.is_novel ? <NovelBadge /> : null}
              {e.variants?.length ? (
                <span className="ml-1 text-[13px] text-[var(--color-neutral-700)]">
                  Also heard as <i>{e.variants.join(", ")}</i>
                </span>
              ) : null}
            </div>
          </div>
          <PronounceButton audioUrl={occ?.audio_url ?? null} className="justify-self-start" />
        </div>

        {/* Evidence */}
        {occ ? (
          <div className="grid grid-cols-[minmax(0,1fr)] gap-6 border-b-2 border-[var(--color-divider)] py-8 lg:grid-cols-[minmax(0,1fr)_260px]">
            <EvidenceClip
              clipUrl={e.clip_url}
              tStart={occ.t_start}
              tEnd={occ.t_end}
              source={occ.source}
              timeSource={occ.time_source}
            />
            <CropView
              cropUrl={e.crop_url}
              overlayUrl={e.overlay_url}
              keyframeUrl={e.keyframe_url}
              samStatus={e.sam_status}
            />
          </div>
        ) : null}

        {/* Quote */}
        {occ?.evidence_quote ? (
          <section className="grid grid-cols-[minmax(0,1fr)] gap-2 border-b-2 border-[var(--color-divider)] py-8 lg:grid-cols-[200px_minmax(0,1fr)] lg:gap-6">
            <h2 className="label m-0 pt-1.5">{quoteLabel(occ.source, occ.t_start)}</h2>
            <p className="m-0 text-[22px] leading-[1.3] tracking-[-0.01em] text-pretty lg:text-[30px]">
              <QuoteBody source={occ.source} text={occ.evidence_quote} />
            </p>
          </section>
        ) : null}

        {/* Meaning */}
        <section className="grid grid-cols-[minmax(0,1fr)] gap-4 border-b-2 border-[var(--color-divider)] py-8 lg:grid-cols-[200px_minmax(0,1fr)_minmax(0,1fr)] lg:gap-6">
          <h2 className="label m-0 pt-1.5">Meaning</h2>
          <div>
            <div className="text-[12px] text-[var(--color-neutral-700)]">English</div>
            <div className="font-heading mt-0.5 text-[20px] leading-tight lg:text-[24px]">
              {e.gloss_en}
            </div>
          </div>
          <div className="lg:border-l lg:border-[var(--color-divider)] lg:pl-6">
            <div className="text-[12px] text-[var(--color-neutral-700)]">Bahasa Indonesia</div>
            <div className="font-heading mt-0.5 text-[20px] leading-tight lg:text-[24px]">
              {e.gloss_id}
            </div>
          </div>
          {e.maestro_note ? (
            <p className="text-[13px] text-[var(--color-neutral-700)] lg:col-span-2 lg:col-start-2">
              Maker&apos;s note · {e.maestro_note}
            </p>
          ) : null}
        </section>

        {/* Confidence / source / validation */}
        <section className="grid grid-cols-[minmax(0,1fr)] gap-3 border-b-2 border-[var(--color-divider)] py-5 text-[14px] lg:grid-cols-[200px_repeat(3,minmax(0,1fr))] lg:items-center lg:gap-6">
          <h2 className="label m-0">Confidence</h2>
          <div>
            {conf === "high" || conf === "medium" || conf === "low" ? (
              <ConfidenceTag confidence={conf} />
            ) : (
              <span className="text-[var(--color-neutral-700)]">—</span>
            )}
          </div>
          <div>
            <SourceBadge source={source} />
          </div>
          <div>
            <ValidationLabel variant={e.status === "proposed" ? "proposed" : "documenter"} />
          </div>
        </section>

        {/* Occurrences + source card */}
        <section className="grid grid-cols-[minmax(0,1fr)] gap-6 py-8 lg:grid-cols-[200px_minmax(0,1fr)_320px]">
          <h2 className="label m-0 pt-1">
            Heard in {e.occurrences?.length ?? 0} recordings
          </h2>
          <div>
            {e.occurrences?.length ? (
              <OccurrenceList occurrences={e.occurrences} />
            ) : (
              <p className="text-[13px] text-[var(--color-neutral-700)]">
                No public occurrence for this entry.
              </p>
            )}
            {occ ? (
              <Link
                href={`/d/${slug}/map/${occ.recording_id}`}
                className="mt-4 inline-block text-[13px]"
              >
                {COPY.ui.seeInProcessMap}
              </Link>
            ) : null}
          </div>
          <div className="flex flex-col gap-4">
            <SourceCard
              title={occ?.recording_title ?? null}
              contributor={e.contributor_name}
              attribution={e.attribution}
            />
          </div>
        </section>
      </main>
      <PublicFooter />
    </>
  );
}
