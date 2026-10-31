"use client";

import { useEffect, useState } from "react";
import { AskPanel } from "@/components/AskPanel";
import { StudioKeyGate } from "@/components/StudioKeyGate";
import { apiGet } from "@/lib/api";
import { COPY } from "@/lib/copy";
import type { Archive } from "@/lib/types";

function StudioAsk() {
  const [archives, setArchives] = useState<Archive[] | null>(null);
  const [archiveId, setArchiveId] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiGet<Archive[]>("/api/archives")
      .then((rows) => {
        if (cancelled) return;
        setArchives(rows);
        const first = rows.find((a) => !a.slug.includes("sandbox")) ?? rows[0];
        setArchiveId(first?.id ?? null);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto w-full max-w-[900px] px-6 py-8">
      <p className="label m-0">Studio</p>
      <h1 className="mt-1 text-[30px] leading-none tracking-[-0.02em]">
        {COPY.ask.title}
      </h1>
      <p className="mt-2 max-w-[620px] text-[14px] text-[var(--color-neutral-800)]">
        {COPY.ask.studioIntro}
      </p>

      {failed ? (
        <div className="empty mt-6">
          <span>{COPY.ask.unavailable}</span>
        </div>
      ) : null}

      {archives === null && !failed ? (
        <p className="mt-6 text-[13px] text-[var(--color-neutral-700)]">{COPY.ask.thinking}</p>
      ) : null}

      {archives && archives.length === 0 ? (
        <div className="empty mt-6">
          <span>{COPY.empty.dictionary}</span>
        </div>
      ) : null}

      {archives && archives.length > 0 ? (
        <>
          <div className="field mt-6 max-w-[320px]">
            <label htmlFor="ask-archive">Archive</label>
            <select
              id="ask-archive"
              className="input"
              value={archiveId ?? ""}
              onChange={(event) => setArchiveId(Number(event.target.value))}
            >
              {archives.map((archive) => (
                <option key={archive.id} value={archive.id}>
                  {archive.title}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-6 border-t-2 border-[var(--color-divider)] pt-6">
            {archiveId ? (
              <AskPanel
                key={archiveId}
                endpoint={`/api/archives/${archiveId}/ask`}
                studio
              />
            ) : null}
          </div>
        </>
      ) : null}
    </main>
  );
}

export default function StudioAskPage() {
  return (
    <StudioKeyGate>
      <StudioAsk />
    </StudioKeyGate>
  );
}
