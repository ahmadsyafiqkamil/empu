import Link from "next/link";
import type { EntryListItem } from "@/lib/types";
import { NovelBadge } from "./NovelBadge";
import { SourceBadge } from "./SourceBadge";

/** Dictionary cell: 88px frame on desktop, 56px on mobile. Frames stay 4:5 and contain. */
export function EntryRow({ slug, e }: { slug: string; e: EntryListItem }) {
  const thumb = e.crop_url ?? e.keyframe_url ?? null;
  return (
    <Link
      href={`/d/${slug}/${e.id}`}
      className="grid grid-cols-[56px_minmax(0,1fr)] items-start gap-3 border-b border-[var(--color-divider)] py-3 text-[var(--color-text)] no-underline hover:bg-[var(--color-surface)] md:grid-cols-[88px_minmax(0,1fr)] md:gap-3.5 md:pt-4 md:pb-4 md:pr-4"
    >
      <div className="frame-media grid aspect-4/5 w-full place-items-center bg-[var(--color-surface)]">
        {thumb ? (
          // Frame URL only — original recording stills, never generated images.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumb} alt="" className="size-full object-contain" />
        ) : null}
      </div>

      <div className="flex min-w-0 flex-col gap-1">
        <span className="font-heading text-[19px] leading-[1.1] tracking-[-0.01em] md:text-[22px]">
          {e.term}
        </span>
        <span className="line-clamp-2 text-[13px] leading-snug text-[var(--color-neutral-800)]">
          {e.gloss_en}
        </span>
        <span className="mt-auto flex flex-wrap items-center gap-2 pt-1">
          <SourceBadge source={e.source} size="sm" />
          {e.is_novel ? <NovelBadge compact /> : null}
        </span>
      </div>
    </Link>
  );
}
