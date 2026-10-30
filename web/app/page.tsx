import Link from "next/link";
import { COPY } from "@/lib/copy";
import type { Archive } from "@/lib/types";
import { ArchivePicker } from "@/components/ArchivePicker";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export default async function Home() {
  const archives: Archive[] = await fetch(`${API}/api/public/archives`, { cache: "no-store" })
    .then((r) => r.json())
    .catch(() => []);

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <ArchivePicker archives={archives} />

      {/* How it works — 3 steps */}
      <section className="mt-16">
        <h2 className="font-display text-2xl">How it works</h2>
        <ol className="mt-4 space-y-3">
          {COPY.home.steps.map((step, i) => (
            <li key={i} className="flex gap-4">
              <span className="font-mono text-sm text-[var(--wax)]">{i + 1}</span>
              <span className="max-w-xl">{step}</span>
            </li>
          ))}
        </ol>
      </section>

      {/* Principles */}
      <section className="mt-12">
        <h2 className="font-display text-2xl">Principles</h2>
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {COPY.home.principles.map((p, i) => (
            <li key={i} className="border border-[var(--line)] p-3 text-sm">
              {p}
            </li>
          ))}
        </ul>
      </section>

      {/* Vision */}
      <p className="mt-16 font-display text-xl italic">{COPY.home.vision}</p>

      {/* Footer */}
      <footer className="mt-16 space-y-2 border-t border-[var(--line)] pt-6 text-xs text-[var(--muted)]">
        <p>{COPY.home.frameAttribution}</p>
        <p>{COPY.footer}</p>
        <p>
          <Link href="/studio" className="underline">
            Documenter studio
          </Link>
        </p>
      </footer>
    </main>
  );
}