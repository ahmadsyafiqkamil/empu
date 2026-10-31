import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { COPY } from "@/lib/copy";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

type ClipRow = {
  speech_recall?: number | null;
  speech_precision?: number | null;
  median_time_error_s?: number | null;
  source_accuracy?: number | null;
  baseline_speech_recall?: number | null;
  n_pred_speech?: number | null;
};

function fmt(v: number | null | undefined, digits = 2) {
  return v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(digits);
}

function mean(values: (number | null | undefined)[]): number | null {
  const nums = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
}

export default async function EvidencePage() {
  const data = await fetch(`${API}/api/eval/summary`, { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);

  const clips: Record<string, ClipRow> = data?.clips ?? {};
  const rows = Object.entries(clips);
  const musicOnly = clips["kontrol-musik-nglorod"]?.n_pred_speech ?? null;

  const stats = [
    { label: "Clips measured", value: rows.length || "—" },
    { label: "Speech recall (mean)", value: fmt(mean(rows.map(([, m]) => m.speech_recall))) },
    { label: "Precision (mean)", value: fmt(mean(rows.map(([, m]) => m.speech_precision))) },
    {
      label: "Music-only control",
      value: musicOnly == null ? "—" : `${musicOnly} spoken`,
    },
  ];

  return (
    <>
      <PublicHeader />
      <main className="mx-auto w-full max-w-[1100px] px-5 pt-8 pb-16 lg:px-0">
        <p className="label">Evidence</p>
        <h1 className="mt-2 mb-0 text-[34px] leading-[0.98] tracking-[-0.03em] md:text-[44px] lg:text-[56px]">
          {COPY.evidence.title}
        </h1>
        <p className="mt-3 max-w-[720px] text-[15px] text-[var(--color-neutral-800)]">
          {COPY.evidence.subtitle}
        </p>
        {data ? (
          <p className="mono mt-2 text-[12px] text-[var(--color-neutral-700)]">
            {[data.pack, data.mode ? `mode ${data.mode}` : null, data.created_at]
              .filter(Boolean)
              .join(" · ")}
          </p>
        ) : null}

        <div className="mt-8 grid grid-cols-[minmax(0,1fr)] border-t-2 border-l-2 border-[var(--color-divider)] sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s) => (
            <div
              key={s.label}
              className="border-r-2 border-b-2 border-[var(--color-divider)] px-5 py-6"
            >
              <div className="text-[12px] text-[var(--color-neutral-700)]">{s.label}</div>
              <div className="font-heading mt-1 text-[32px] leading-none tracking-[-0.02em] lg:text-[40px]">
                {s.value}
              </div>
            </div>
          ))}
        </div>

        {rows.length === 0 ? (
          <div className="empty mt-8">
            <span>
              No evaluation run yet. Numbers appear here only from a real gold-annotation run —
              never placeholders.
            </span>
            <span className="mono text-[12px] text-[var(--color-neutral-700)]">
              empu eval run
            </span>
          </div>
        ) : (
          <div className="mt-8 overflow-x-auto">
            <table className="table min-w-[720px]">
              <thead>
                <tr>
                  <th>Clip</th>
                  <th>Speech recall</th>
                  <th>Precision</th>
                  <th>Median |Δt|</th>
                  <th>Source acc.</th>
                  <th>ASR baseline</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(([id, m]) => (
                  <tr key={id}>
                    <td className="mono text-[13px]">{id}</td>
                    <td>{fmt(m.speech_recall)}</td>
                    <td>{fmt(m.speech_precision)}</td>
                    <td className="mono">
                      {m.median_time_error_s == null ? "—" : `${fmt(m.median_time_error_s, 1)}s`}
                    </td>
                    <td>{fmt(m.source_accuracy)}</td>
                    <td>{fmt(m.baseline_speech_recall)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <section className="mt-10 grid grid-cols-[minmax(0,1fr)] gap-4 border-t-2 border-[var(--color-divider)] pt-6 lg:grid-cols-[200px_minmax(0,1fr)] lg:gap-6">
          <h2 className="label m-0 pt-0.5">Limits</h2>
          <div className="flex flex-col gap-2 text-[14px] text-[var(--color-neutral-800)]">
            <p className="m-0">{COPY.evidence.limitSource}</p>
            <p className="m-0">{COPY.evidence.limitTime}</p>
            <p className="m-0">
              Demo clips are CC BY videos that were already edited, not field recordings.
            </p>
          </div>
        </section>

        <section className="mt-8 grid grid-cols-[minmax(0,1fr)] gap-4 border-t-2 border-[var(--color-divider)] pt-6 lg:grid-cols-[200px_minmax(0,1fr)] lg:gap-6">
          <h2 className="label m-0 pt-0.5">Method</h2>
          <ol className="m-0 flex list-none flex-col gap-2 p-0 text-[14px] text-[var(--color-neutral-800)]">
            <li>75-second segments, structured output per segment.</li>
            <li>faster-whisper anchors each timestamp to a word-level transcript.</li>
            <li>SAM 3.1 returns bounding boxes, not masks; crops stay inside the original frame.</li>
            <li>Every gold mention is checked by a person before it counts.</li>
          </ol>
        </section>
      </main>
      <PublicFooter />
    </>
  );
}
