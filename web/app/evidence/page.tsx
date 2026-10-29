import { COPY } from "@/lib/copy";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

function fmt(v: number | null | undefined) {
  return v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(2);
}

export default async function EvidencePage() {
  const data = await fetch(`${API}/api/eval/summary`, { cache: "no-store" })
    .then((r) => r.json())
    .catch(() => ({}));
  const clips = data.clips ?? {};

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="font-display text-3xl">{COPY.evidence.title}</h1>
      <p className="mt-2 text-sm text-[var(--muted)]">{COPY.evidence.subtitle}</p>

      <table className="mt-8 w-full text-left text-sm">
        <thead>
          <tr className="border-b border-[var(--line)]">
            <th className="py-2">Clip</th>
            <th>Speech recall</th>
            <th>Precision</th>
            <th>Median |Δt|</th>
            <th>Source acc.</th>
            <th>ASR baseline</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(clips as Record<string, Record<string, number | null>>).map(
            ([id, m]) => (
              <tr key={id} className="border-b border-[var(--line)]">
                <td className="py-2">{id}</td>
                <td>{fmt(m.speech_recall)}</td>
                <td>{fmt(m.speech_precision)}</td>
                <td>{m.median_time_error_s ?? "—"}</td>
                <td>{fmt(m.source_accuracy)}</td>
                <td>{fmt(m.baseline_speech_recall)}</td>
              </tr>
            ),
          )}
        </tbody>
      </table>

      <p className="mt-6 text-sm">
        Music-only control:{" "}
        {String(
          (clips as Record<string, { n_pred_speech?: number }>)["kontrol-musik-nglorod"]
            ?.n_pred_speech ?? "—",
        )}{" "}
        spoken terms (target 0).
      </p>

      <p className="mt-6 text-xs text-[var(--muted)]">
        {COPY.evidence.limitSource} {COPY.evidence.limitTime} Demo clips are CC BY videos,
        already edited, not field recordings.
      </p>
      <p className="mt-2 text-xs text-[var(--muted)]">
        Method: 75-second segments · structured output · faster-whisper as the time anchor · SAM
        bounding boxes.
      </p>
    </main>
  );
}