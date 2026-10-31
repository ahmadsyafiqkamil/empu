"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AskEvidenceCard } from "./AskEvidenceCard";
import { COPY } from "@/lib/copy";
import { AskHttpError, askErrorCopy, isAskable, normalizeQuestion, postQuestion } from "@/lib/ask";
import type { AskAnswer } from "@/lib/types";

type Turn = { id: number; question: string; answer: AskAnswer | null; error: string | null };

function openingTurn(question: string): Turn {
  return { id: 1, question: normalizeQuestion(question), answer: null, error: null };
}

/**
 * The conversation surface. One question, one answer, no cross-turn context sent
 * to the model: each question is answered from the archive on its own.
 */
export function AskPanel({
  endpoint,
  suggestions = [],
  slug = "",
  studio = false,
  initialQuestion = "",
  autoSend = false,
}: {
  endpoint: string;
  suggestions?: string[];
  slug?: string;
  studio?: boolean;
  initialQuestion?: string;
  autoSend?: boolean;
}) {
  const opensWithQuestion = autoSend && isAskable(initialQuestion);
  const [draft, setDraft] = useState(opensWithQuestion ? "" : initialQuestion);
  const [turns, setTurns] = useState<Turn[]>(() =>
    opensWithQuestion ? [openingTurn(initialQuestion)] : [],
  );
  const [pending, setPending] = useState(opensWithQuestion);
  const abortRef = useRef<AbortController | null>(null);
  const nextTurnId = useRef(opensWithQuestion ? 1 : 0);

  const resolve = useCallback(
    (question: string, turnId: number, controller: AbortController) => {
      postQuestion(endpoint, question, controller.signal)
        .then((answer) => {
          setTurns((prev) => patch(prev, turnId, { answer }));
        })
        .catch((error: unknown) => {
          if ((error as Error)?.name === "AbortError") return;
          const message =
            error instanceof AskHttpError ? askErrorCopy(error.status) : COPY.ask.failed;
          setTurns((prev) => patch(prev, turnId, { error: message }));
        })
        .finally(() => {
          setPending(false);
        });
    },
    [endpoint],
  );

  useEffect(() => {
    if (!opensWithQuestion) return;
    const controller = new AbortController();
    abortRef.current = controller;
    resolve(normalizeQuestion(initialQuestion), 1, controller);
    return () => controller.abort();
    // Runs once per mounted panel: the panel is keyed by the store token.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = (raw: string) => {
    const question = normalizeQuestion(raw);
    if (!isAskable(question) || !endpoint) return;
    // One question at a time: the button is disabled while pending, and Enter must
    // match it. Aborting here would strand the previous turn on "thinking".
    if (pending) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    nextTurnId.current += 1;
    const id = nextTurnId.current;
    setPending(true);
    setDraft("");
    setTurns((prev) => [...prev, { id, question, answer: null, error: null }]);
    resolve(question, id, controller);
  };

  return (
    <div className="flex flex-col gap-5">
      <form
        className="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          send(draft);
        }}
      >
        <label className="field-label" htmlFor="ask-question">
          {COPY.ask.title}
        </label>
        <textarea
          id="ask-question"
          className="input"
          autoFocus
          value={draft}
          maxLength={500}
          placeholder={COPY.ask.placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              send(draft);
            }
          }}
        />
        <div className="flex flex-wrap items-center gap-2">
          <button type="submit" className="btn btn-primary" disabled={pending || !isAskable(draft)}>
            {pending ? COPY.ask.thinking : COPY.ask.submit}
          </button>
          {suggestions.length > 0 && !pending ? (
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="btn btn-secondary text-[12px]"
                  onClick={() => send(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        {studio ? (
          <p className="m-0 text-[12px] text-[var(--color-neutral-700)]">{COPY.ask.studioNote}</p>
        ) : null}
      </form>

      <div className="flex flex-col gap-6" aria-live="polite">
        {turns.length === 0 ? (
          <p className="m-0 text-[13px] text-[var(--color-neutral-700)]">{COPY.ask.intro}</p>
        ) : null}

        {turns.map((turn) => (
          <section key={turn.id} className="flex flex-col gap-3">
            <p className="m-0 border-l-2 border-[var(--color-divider)] pl-3 text-[13px] font-semibold">
              {turn.question}
            </p>

            {turn.error ? (
              <div className="empty">
                <span>{turn.error}</span>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={pending}
                  onClick={() => send(turn.question)}
                >
                  {COPY.ask.retry}
                </button>
              </div>
            ) : null}

            {!turn.answer && !turn.error ? (
              <p className="m-0 text-[13px] text-[var(--color-neutral-700)]">
                {COPY.ask.thinking}
              </p>
            ) : null}

            {turn.answer?.refused ? (
              <div className="empty">
                <span>{turn.answer.answer || COPY.ask.refused}</span>
              </div>
            ) : null}

            {turn.answer && !turn.answer.refused ? (
              <>
                <p className="m-0 text-[15px] leading-relaxed">{turn.answer.answer}</p>
                {turn.answer.evidence.length > 0 ? (
                  <div className="flex flex-col gap-2">
                    <h2 className="label m-0">{COPY.ask.evidence}</h2>
                    {turn.answer.evidence.map((evidence) => (
                      <AskEvidenceCard
                        key={`${evidence.entry.id}-${evidence.occurrence.id}`}
                        evidence={evidence}
                        slug={slug}
                        studio={studio}
                      />
                    ))}
                  </div>
                ) : null}
              </>
            ) : null}
          </section>
        ))}
      </div>
    </div>
  );
}

function patch(turns: Turn[], id: number, change: Partial<Turn>): Turn[] {
  return turns.map((turn) => (turn.id === id ? { ...turn, ...change } : turn));
}
