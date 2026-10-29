"use client";

import { useEffect, useState } from "react";
import { StudioKeyGate } from "@/components/StudioKeyGate";
import { apiGet, getStudioKey, studioHeaders } from "@/lib/api";
import { COPY } from "@/lib/copy";
import type { Archive } from "@/lib/types";

const FORMATS = [
  { id: "json", ext: "json", name: "JSON dataset", desc: "Entries, recordings, process maps, and attribution in one file." },
  { id: "csv", ext: "csv", name: "CSV table", desc: "One row per occurrence with its source label." },
  { id: "eaf", ext: "eaf", name: "ELAN .eaf", desc: "Time-aligned tiers for one recording." },
  { id: "zip", ext: "zip", name: "ZIP", desc: "JSON + CSV + ELAN + clips, crops, and README attribution." },
] as const;

function Form() {
  const [archives, setArchives] = useState<Archive[]>([]);
  const [archiveId, setArchiveId] = useState<number | null>(null);
  const [format, setFormat] = useState<string>("json");
  const [scope, setScope] = useState<"public" | "all">("public");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet<Archive[]>("/api/archives").then(setArchives).catch(() => setArchives([]));
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
      className="mx-auto max-w-2xl space-y-6 p-8"
      onSubmit={(e) => {
        e.preventDefault();
        download();
      }}
    >
      <h1 className="text-2xl">Export</h1>

      <div className="space-y-1">
        <label htmlFor="archive" className="text-sm text-[var(--muted)]">
          Archive
        </label>
        <select
          id="archive"
          value={selectedId ?? ""}
          onChange={(e) => setArchiveId(Number(e.target.value))}
          className="w-full border border-[var(--line)] bg-transparent px-3 py-2"
        >
          {archives.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title}
            </option>
          ))}
        </select>
      </div>

      <fieldset>
        <legend className="text-sm text-[var(--muted)]">Format</legend>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {FORMATS.map((f) => {
            const active = format === f.id;
            return (
              <label
                key={f.id}
                className={`block cursor-pointer border p-3 ${
                  active
                    ? "border-[var(--accent)] bg-[var(--surface)]"
                    : "border-[var(--line)] bg-transparent"
                }`}
              >
                <input
                  type="radio"
                  name="format"
                  value={f.id}
                  checked={active}
                  onChange={() => setFormat(f.id)}
                  className="sr-only"
                />
                <span className="block font-medium">{f.name}</span>
                <span className="mt-1 block text-xs text-[var(--muted)]">{f.desc}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm text-[var(--muted)]">Scope</legend>
        <label className="block text-sm">
          <input
            type="radio"
            name="scope"
            value="public"
            checked={scope === "public"}
            onChange={() => setScope("public")}
          />{" "}
          {COPY.export.publicOnly}
        </label>
        {getStudioKey() ? (
          <label className="block text-sm">
            <input
              type="radio"
              name="scope"
              value="all"
              checked={scope === "all"}
              onChange={() => setScope("all")}
            />{" "}
            {COPY.export.everything}
          </label>
        ) : null}
      </fieldset>

      <p className="text-xs text-[var(--muted)]">{COPY.export.note}</p>

      <button
        disabled={busy || selectedId === null}
        className="bg-[var(--accent)] px-4 py-2 text-[var(--bg)] disabled:opacity-50"
      >
        {busy ? "Downloading…" : "Download"}
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