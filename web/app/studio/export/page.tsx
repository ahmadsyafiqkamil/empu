"use client";

import { useEffect, useState } from "react";
import { StudioKeyGate } from "@/components/StudioKeyGate";
import { apiGet, getStudioKey, studioHeaders } from "@/lib/api";
import { COPY } from "@/lib/copy";
import type { Archive } from "@/lib/types";

const FORMATS = [
  {
    id: "json",
    ext: "json",
    name: "JSON dataset",
    desc: "Entries, recordings, process maps, and attribution in one file.",
  },
  {
    id: "csv",
    ext: "csv",
    name: "CSV table",
    desc: "One row per occurrence with its source label.",
  },
  {
    id: "eaf",
    ext: "eaf",
    name: "ELAN .eaf",
    desc: "Time-aligned tiers for one recording.",
  },
  {
    id: "zip",
    ext: "zip",
    name: "ZIP",
    desc: "JSON + CSV + ELAN + clips, crops, and README attribution.",
  },
] as const;

function Form() {
  const [archives, setArchives] = useState<Archive[]>([]);
  const [archiveId, setArchiveId] = useState<number | null>(null);
  const [format, setFormat] = useState<string>("json");
  const [scope, setScope] = useState<"public" | "all">("public");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet<Archive[]>("/api/archives")
      .then(setArchives)
      .catch(() => setArchives([]));
  }, []);

  const selectedId = archiveId ?? archives[0]?.id ?? null;

  function download() {
    if (selectedId === null || busy) return;
    setBusy(true);
    const ext = FORMATS.find((f) => f.id === format)?.ext ?? "txt";
    const url = `/api/archives/${selectedId}/export?format=${format}&scope=${scope}`;
    void (async () => {
      try {
        const r = await fetch(url, { headers: studioHeaders() });
        if (!r.ok) throw new Error(`${r.status}`);
        const blob = await r.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `empu-${scope}.${ext}`;
        a.click();
        URL.revokeObjectURL(a.href);
      } finally {
        setBusy(false);
      }
    })();
  }

  return (
    <form
      className="mx-auto w-full max-w-[900px] px-5 py-10 lg:px-0 lg:py-12"
      onSubmit={(e) => {
        e.preventDefault();
        download();
      }}
    >
      <h1 className="m-0 text-[32px] tracking-[-0.02em] lg:text-[42px]">Export</h1>
      <p className="mt-1 text-[15px] text-[var(--color-neutral-800)]">
        Take the archive out. Every file keeps its creator attribution and license.
      </p>

      <div className="mt-8 grid grid-cols-[minmax(0,1fr)] items-end gap-3 md:grid-cols-[1fr_auto]">
        <label className="field">
          <span className="field-label">Archive</span>
          <select
            value={selectedId ?? ""}
            onChange={(e) => setArchiveId(Number(e.target.value))}
            className="input h-11"
            aria-label="Archive"
          >
            {archives.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
          </select>
        </label>
      </div>

      <fieldset className="mt-8 border-0 p-0">
        <legend className="label mb-2">Format</legend>
        <div className="grid grid-cols-[minmax(0,1fr)] border-t-2 border-l-2 border-[var(--color-divider)] sm:grid-cols-2">
          {FORMATS.map((f) => {
            const active = format === f.id;
            return (
              <label
                key={f.id}
                className="flex cursor-pointer flex-col gap-1 border-r-2 border-b-2 border-[var(--color-divider)] p-4"
                style={
                  active
                    ? { background: "var(--color-text)", color: "var(--color-bg)" }
                    : undefined
                }
              >
                <input
                  type="radio"
                  name="format"
                  value={f.id}
                  checked={active}
                  onChange={() => setFormat(f.id)}
                  className="sr-only"
                />
                <span className="font-heading text-[17px]">{f.name}</span>
                <span
                  className="text-[13px]"
                  style={{ color: active ? undefined : "var(--color-neutral-700)" }}
                >
                  {f.desc}
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="mt-8 border-0 p-0">
        <legend className="label mb-2">Scope</legend>
        <div className="flex flex-col gap-2 text-[14px]">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="scope"
              value="public"
              checked={scope === "public"}
              onChange={() => setScope("public")}
              className="accent-[var(--color-accent)]"
            />
            {COPY.export.publicOnly}
          </label>
          {getStudioKey() ? (
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="scope"
                value="all"
                checked={scope === "all"}
                onChange={() => setScope("all")}
                className="accent-[var(--color-accent)]"
              />
              {COPY.export.everything}
            </label>
          ) : null}
        </div>
      </fieldset>

      <p className="mt-6 text-[13px] text-[var(--color-neutral-700)]">{COPY.export.note}</p>

      <button
        disabled={busy || selectedId === null}
        className="btn btn-primary mt-2 h-12 min-w-[180px] justify-start px-5"
      >
        {busy ? "Downloading…" : "Download"}
        <span className="ml-auto" aria-hidden>
          ↓
        </span>
      </button>
    </form>
  );
}

export default function ExportPage() {
  return (
    <StudioKeyGate>
      <Form />
    </StudioKeyGate>
  );
}
