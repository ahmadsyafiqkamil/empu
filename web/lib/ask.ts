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

export type ArchiveTerms = { title: string; terms: string[] };

/**
 * One suggestion per archive, round-robin, so a large archive does not hide a
 * small one. Ask answers from every archive, and the chips should say so.
 */
export function askSuggestionsAcross(archives: ArchiveTerms[], n = 3): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const longest = Math.max(0, ...archives.map((archive) => archive.terms.length));
  for (let i = 0; i < longest; i += 1) {
    for (const archive of archives) {
      const term = (archive.terms[i] ?? "").trim();
      if (!term) continue;
      const question = `What is ${term}?`;
      if (seen.has(question)) continue;
      seen.add(question);
      out.push(question);
      if (out.length >= n) return out;
    }
  }
  return out;
}

export function askErrorCopy(status: number): string {
  if (status === 429) return COPY.ask.rateLimited;
  if (status === 502 || status === 503) return COPY.ask.unavailable;
  return COPY.ask.failed;
}

export class AskHttpError extends Error {
  constructor(public readonly status: number) {
    super(`ask failed with ${status}`);
    this.name = "AskHttpError";
  }
}

/** POST one question. Kept out of the component so it can be called from callbacks. */
export async function postQuestion(
  endpoint: string,
  question: string,
  signal?: AbortSignal,
): Promise<import("./types").AskAnswer> {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!response.ok) throw new AskHttpError(response.status);
  return (await response.json()) as import("./types").AskAnswer;
}
