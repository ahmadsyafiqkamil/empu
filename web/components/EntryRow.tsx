import Link from "next/link";
import type { EntryListItem } from "@/lib/types";
import { NovelBadge } from "./NovelBadge";
import { SourceBadge } from "./SourceBadge";

export function EntryRow({ slug, e }: { slug: string; e: EntryListItem }) {
  const thumb = e.keyframe_url ?? e.crop_url ?? null;
  return (
    <Link
      href={`/d/${slug}/${e.id}`}
      className="flex items-center gap-3 py-3 outline-offset-4 outline-[var(--wax)]"
    >
      {thumb ? (
        // Frame URL only — original recording stills, never generated images.
        // eslint-disable-next-line @next/next/no-img-element
        <img alt="" src={thumb} className="h-14 w-14 shrink-0 object-cover" />
      ) : (
        <span className="h-14 w-14 shrink-0 border border-[var(--line)]" />
      )}
      <span className="min-w-0 flex-1">
        <span className="block truncate font-display text-lg leading-tight">{e.term}</span>
        <span className="block truncate text-sm text-[var(--muted)]">{e.gloss_en}</span>
      </span>
      <span className="flex shrink-0 items-center gap-2">
        {e.is_novel ? <NovelBadge /> : null}
        <SourceBadge source={e.source} size="sm" />
      </span>
    </Link>
  );
}