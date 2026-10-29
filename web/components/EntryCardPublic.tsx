import Link from "next/link";
import { CATEGORY_LABEL } from "@/lib/copy";
import type { EntryListItem } from "@/lib/types";
import { NovelBadge } from "./NovelBadge";
import { SourceBadge } from "./SourceBadge";

export function EntryCardPublic({ slug, e }: { slug: string; e: EntryListItem }) {
  const thumb = e.keyframe_url ?? e.crop_url ?? null;
  return (
    <Link
      href={`/d/${slug}/${e.id}`}
      className="block border border-[var(--line)] bg-[var(--surface)] outline-offset-4 outline-[var(--wax)]"
    >
      {thumb ? (
        // Frame URL only — original recording stills, never generated images.
        // eslint-disable-next-line @next/next/no-img-element
        <img alt="" src={thumb} className="aspect-video w-full object-cover" />
      ) : (
        <div className="aspect-video w-full bg-[var(--surface)]" />
      )}
      <div className="space-y-1 p-3">
        <p className="font-display text-xl leading-tight">{e.term}</p>
        <p className="truncate text-sm text-[var(--muted)]">{e.gloss_en}</p>
        <div className="flex items-center justify-between gap-2 pt-1">
          <SourceBadge source={e.source} size="sm" />
          <span className="flex items-center gap-2 text-xs text-[var(--muted)]">
            {e.category ? CATEGORY_LABEL[e.category] ?? e.category : null}
            {e.is_novel ? <NovelBadge /> : null}
          </span>
        </div>
      </div>
    </Link>
  );
}