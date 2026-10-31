import { normalizeQuestion } from "./ask";

/**
 * Where the floating Ask launcher belongs.
 *
 * The launcher is mounted once in the root layout, so every public screen gets it
 * without moving a single page. Studio screens and the Ask page itself are excluded:
 * the first already has its own studio-scoped entry, the second is the panel.
 */
export function shouldShowLauncher(pathname: string): boolean {
  if (pathname.startsWith("/studio")) return false;
  if (pathname.endsWith("/ask")) return false;
  return true;
}

/** `/d/<slug>`, `/d/<slug>/<id>`, `/d/<slug>/<id>/map/<recording>` → `<slug>`. */
export function archiveSlugFromPathname(pathname: string): string | null {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length < 2 || parts[0] !== "d") return null;
  return parts[1] || null;
}

type ArchiveLike = { slug: string; is_demo?: boolean; is_sandbox?: boolean };

/** Prefer the demo archive, never ask a sandbox, and give up quietly otherwise. */
export function pickArchiveSlug(archives: ArchiveLike[]): string | null {
  const usable = archives.filter((a) => !a.is_sandbox);
  const demo = usable.find((a) => a.is_demo);
  return (demo ?? usable[0])?.slug ?? null;
}

export function termQuestion(term: string): string {
  return `What is ${normalizeQuestion(term)}?`;
}

/** The sheet must not stay (or reopen) once the launcher is no longer on screen. */
export function shouldCloseOnHide(visible: boolean, open: boolean): boolean {
  return !visible && open;
}
