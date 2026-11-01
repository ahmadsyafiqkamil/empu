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

export function termQuestion(term: string): string {
  return `What is ${normalizeQuestion(term)}?`;
}

/** The sheet must not stay (or reopen) once the launcher is no longer on screen. */
export function shouldCloseOnHide(visible: boolean, open: boolean): boolean {
  return !visible && open;
}

const TYPING_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

/** True when the focused element is a text field, so a shortcut is not ours to take. */
export function isTypingTarget(tagName: string | null | undefined): boolean {
  if (!tagName) return false;
  return TYPING_TAGS.has(tagName.toUpperCase());
}
