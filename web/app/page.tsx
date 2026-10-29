import Link from "next/link";
import { COPY } from "@/lib/copy";
import type { Archive } from "@/lib/types";
import { CropView } from "@/components/CropView";
import { SourceBadge } from "@/components/SourceBadge";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

const heroCrop = {
  cropUrl: "/design/contoh-crop-canting.png",
  overlayUrl: "/design/contoh-overlay-canting.jpg",
  keyframeUrl: "/design/nyanting-canting-122s.jpg",
};

export default async function Home() {
  const archives: Archive[] = await fetch(`${API}/api/public/archives`, { cache: "no-store" })
    .then((r) => r.json())
    .catch(() => []);
  const demoSrc = archives.find((a) => a.is_demo) ?? archives[0];
  const demoSlug = demoSrc?.slug ?? "batik-tulis";

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      {/* Hero */}
      <section>
        <p className="font-display text-3xl">
          empu<span className="text-[var(--wax)]">.</span>
        </p>
        <h1 className="mt-4 max-w-xl font-display text-4xl leading-tight">{COPY.tagline}</h1>
        <p className="mt-5 max-w-xl text-[var(--muted)]">{COPY.home.paragraph}</p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link href={`/d/${demoSlug}`} className="bg-[var(--accent)] px-4 py-2 text-white">
            {COPY.home.openArchive}
          </Link>
          <Link href="/try" className="border border-[var(--line)] px-4 py-2">
            {COPY.home.tryClip}
          </Link>
          <Link href="/evidence" className="border border-[var(--line)] px-4 py-2">
            {COPY.home.seeEvidence}
          </Link>
        </div>
      </section>

      {/* Frame + attached entry card */}
      <section className="mt-14 grid gap-6 md:grid-cols-2 md:items-start">
        <div className="aspect-video overflow-hidden bg-[var(--surface)]">
          {/* Frame URL only — original recording still, never generated. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={heroCrop.keyframeUrl}
            alt="A master applying wax with a canting, still from the source recording"
            className="h-full w-full object-cover"
          />
        </div>
        <div className="flex flex-col gap-3 border border-[var(--line)] bg-[var(--surface)] p-4">
          <p className="font-display text-2xl">canting</p>
          <SourceBadge source="speech" />
          <CropView
            cropUrl={heroCrop.cropUrl}
            overlayUrl={heroCrop.overlayUrl}
            keyframeUrl={heroCrop.keyframeUrl}
            samStatus="ok"
          />
        </div>
      </section>

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

      {/* Archive cards */}
      <section className="mt-16">
        <h2 className="font-display text-2xl">Living Archive</h2>
        <ul className="mt-4 space-y-3">
          {archives.map((a) => (
            <li key={a.id} className="border border-[var(--line)] p-4">
              <Link href={`/d/${a.slug}`} className="font-display text-xl">
                {a.title} · Batik Tulis
              </Link>
              <p className="mt-1 text-sm text-[var(--muted)]">
                {a.validated_count} validated terms · {a.recording_count} recordings
              </p>
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