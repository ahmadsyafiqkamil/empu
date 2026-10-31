import { COPY } from "./copy";

export const ASK_MIN_CHARS = 3;
export const ASK_MAX_CHARS = 500;

/** Collapse runs of whitespace so the same question maps to the same cache key. */
export function normalizeQuestion(question: string): string {
  return question.trim().replace(/\s+/g, " ");
}

export function isAskable(question: string): boolean {
  const q = normalizeQuestion(question);
  return q.length >= ASK_MIN_CHARS && q.length <= ASK_MAX_CHARS;
}

export function askSuggestions(
  entries: Pick<{ term: string }, "term">[],
  n = 3,
): string[] {
  const out: string[] = [];
  for (const entry of entries) {
    const term = entry.term.trim();
    if (!term) continue;
    const question = `What is ${term}?`;
    if (!out.includes(question)) out.push(question);
    if (out.length >= n) break;
  }
  return out;
}

export function askErrorCopy(status: number): string {
  if (status === 429) return COPY.ask.rateLimited;
  if (status === 502 || status === 503) return COPY.ask.unavailable;
  return COPY.ask.failed;
}
