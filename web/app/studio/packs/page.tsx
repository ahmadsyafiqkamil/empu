"use client";

import { useCallback, useEffect, useState } from "react";
import { StudioKeyGate } from "@/components/StudioKeyGate";
import { apiGet, apiSend } from "@/lib/api";
import type { Pack, PackDetail } from "@/lib/types";

const PLACEHOLDER = `id: tenun
version: 0.1.0
name: {id: Tenun, en: Hand-weaving}
languages: [id]
prompt_context: >
  Konteks keahlian untuk membantu analisis Muse.

stages:
  - id: menyiapkan
    label: {id: Menyiapkan benang, en: Preparing the yarn}
    variants: [menggulung]

terms:
  - id: lungsi
    label: lungsi
    category: material
    variants: [benang lungsi]
    gloss_id: benang memanjang
    gloss_en: the warp yarn
    visual: false
    verified: false
`;

type ValidateResult = PackDetail & { ok: true } | { ok: false; error: string };

function Form() {
  const [packs, setPacks] = useState<Pack[]>([]);
  const [yaml, setYaml] = useState("");
  const [result, setResult] = useState<ValidateResult | null>(null);
  const [busy, setBusy] = useState<"validate" | "create" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    apiGet<Pack[]>("/api/packs")
      .then(setPacks)
      .catch(() => setPacks([]));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function validate() {
    setBusy("validate");
    setError(null);
    setResult(null);
    try {
      const r = await apiSend<PackDetail>("/api/packs/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml }),
      });
      setResult({ ...r, ok: true });
    } catch (e) {
      const msg = String(e);
      setResult({ ok: false, error: msg.replace(/^400\s*/, "") });
    } finally {
      setBusy(null);
    }
  }

  async function create() {
    setBusy("create");
    setError(null);
    try {
      const r = await apiSend<{ id: string }>("/api/packs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml }),
      });
      setYaml("");
      setResult(null);
      setError(null);
      await refresh();
      void r;
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-8">
      <div>
        <h1 className="text-2xl">Craft packs</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          A craft pack holds a skill&apos;s vocabulary, stages, and SAM prompts. Create one from YAML.
        </p>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-medium">Existing packs</h2>
        <ul className="divide-y divide-[var(--line)] border border-[var(--line)]">
          {packs.length === 0 ? (
            <li className="p-3 text-sm text-[var(--muted)]">No packs yet.</li>
          ) : (
            packs.map((p) => (
              <li key={p.id} className="flex items-baseline justify-between gap-3 p-3 text-sm">
                <span className="font-medium">{p.name.id}</span>
                <span className="font-mono text-xs text-[var(--muted)]">
                  {p.id} · v{p.version}
                </span>
              </li>
            ))
          )}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-medium">New pack</h2>
        <textarea
          value={yaml}
          onChange={(e) => setYaml(e.target.value)}
          spellCheck={false}
          placeholder={PLACEHOLDER}
          className="h-96 w-full resize-y border border-[var(--line)] bg-[var(--surface)] p-3 font-mono text-xs leading-relaxed focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
        />
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void validate()}
            disabled={busy !== null || !yaml.trim()}
            className="border border-[var(--line)] px-4 py-2 disabled:opacity-40"
          >
            {busy === "validate" ? "Validating…" : "Validate"}
          </button>
          <button
            type="button"
            onClick={() => void create()}
            disabled={busy !== null || !yaml.trim()}
            className="bg-[var(--accent)] px-4 py-2 text-black disabled:opacity-40"
          >
            {busy === "create" ? "Creating…" : "Create pack"}
          </button>
        </div>

        {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}

        {result ? (
          result.ok ? (
            <div className="border border-[var(--line)] bg-[var(--surface)] p-3 text-sm">
              <p className="font-medium text-[var(--ok)]">✓ Valid</p>
              <p className="mt-1">
                <span className="font-medium">{result.name.id}</span> · {result.id} · v{result.version}
              </p>
              <p className="text-[var(--muted)]">
                {result.languages?.join(", ")} · {result.n_stages} stages · {result.n_terms} terms
              </p>
            </div>
          ) : (
            <div className="border border-[var(--danger)] bg-[var(--surface)] p-3 text-sm">
              <p className="font-medium text-[var(--danger)]">✗ Invalid</p>
              <pre className="mt-1 whitespace-pre-wrap font-mono text-xs text-[var(--muted)]">
                {result.error}
              </pre>
            </div>
          )
        ) : null}
      </section>
    </div>
  );
}

export default function PackPage() {
  return (
    <StudioKeyGate>
      <Form />
    </StudioKeyGate>
  );
}