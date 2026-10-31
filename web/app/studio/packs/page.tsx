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

type ValidateResult = (PackDetail & { ok: true }) | { ok: false; error: string };

function Form() {
  const [packs, setPacks] = useState<Pack[]>([]);
  const [yaml, setYaml] = useState("");
  const [result, setResult] = useState<ValidateResult | null>(null);
  const [busy, setBusy] = useState<"validate" | "create" | "load" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sourceId, setSourceId] = useState<string | null>(null);

  const refresh = useCallback(() => {
    apiGet<Pack[]>("/api/packs")
      .then(setPacks)
      .catch(() => setPacks([]));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function loadSource(id: string) {
    setBusy("load");
    setError(null);
    try {
      const r = await apiGet<{ yaml: string }>(`/api/packs/${id}/source`);
      setYaml(r.yaml);
      setResult(null);
      setSourceId(id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

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
      setResult({ ok: false, error: String(e).replace(/^400\s*/, "") });
    } finally {
      setBusy(null);
    }
  }

  async function create() {
    setBusy("create");
    setError(null);
    try {
      await apiSend<{ id: string }>("/api/packs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml }),
      });
      setYaml("");
      setResult(null);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto w-full max-w-[1000px] px-5 py-10 lg:px-0 lg:py-12">
      <h1 className="m-0 text-[32px] tracking-[-0.02em] lg:text-[42px]">Craft packs</h1>
      <p className="mt-1 max-w-[640px] text-[15px] text-[var(--color-neutral-800)]">
        A craft pack holds a skill&apos;s vocabulary, stages, and SAM prompts. Add a craft by
        writing one YAML file.
      </p>

      <section className="mt-8">
        <h2 className="label mb-2">Existing packs</h2>
        {packs.length === 0 ? (
          <div className="empty">
            <span>No packs yet.</span>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Pack</th>
                <th>Id</th>
                <th>Version</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {packs.map((p) => (
                <tr key={p.id}>
                  <td className="font-semibold">{p.name.id}</td>
                  <td className="mono text-[13px]">{p.id}</td>
                  <td className="mono text-[13px]">v{p.version}</td>
                  <td className="text-right">
                    <button
                      type="button"
                      onClick={() => void loadSource(p.id)}
                      disabled={busy !== null}
                      className="btn btn-secondary text-[13px]"
                    >
                      {busy === "load" && sourceId === p.id ? "Loading…" : "Load as example"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {sourceId ? (
          <p className="mt-2 text-[12px] text-[var(--color-neutral-700)]">
            Loaded {sourceId}. Edit the id field before creating a new pack.
          </p>
        ) : null}
      </section>

      <section className="mt-8 flex flex-col gap-3">
        <h2 className="label mb-0">New pack</h2>
        <textarea
          value={yaml}
          onChange={(e) => setYaml(e.target.value)}
          spellCheck={false}
          placeholder={PLACEHOLDER}
          aria-label="Craft pack YAML"
          className="input h-96 resize-y font-mono text-[12px] leading-relaxed"
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void validate()}
            disabled={busy !== null || !yaml.trim()}
            className="btn btn-secondary h-10"
          >
            {busy === "validate" ? "Validating…" : "Validate"}
          </button>
          <button
            type="button"
            onClick={() => void create()}
            disabled={busy !== null || !yaml.trim()}
            className="btn btn-primary h-10"
          >
            {busy === "create" ? "Creating…" : "Create pack"}
          </button>
        </div>

        {error ? <p className="m-0 text-[13px] text-[var(--color-accent-700)]">{error}</p> : null}

        {result ? (
          result.ok ? (
            <div className="border-2 border-[var(--color-divider)] p-4 text-[14px]">
              <p className="m-0 font-semibold">✓ Valid</p>
              <p className="mt-1 mb-0">
                {result.name.id} · <span className="mono">{result.id}</span> · v
                {result.version}
              </p>
              <p className="mt-0.5 mb-0 text-[var(--color-neutral-700)]">
                {result.languages?.join(", ")} · {result.n_stages} stages · {result.n_terms} terms
              </p>
            </div>
          ) : (
            <div className="border-2 border-[var(--color-accent-700)] p-4 text-[14px]">
              <p className="m-0 font-semibold text-[var(--color-accent-700)]">✗ Invalid</p>
              <pre className="mono mt-1 mb-0 whitespace-pre-wrap text-[12px] text-[var(--color-neutral-800)]">
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
