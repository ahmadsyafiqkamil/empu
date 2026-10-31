import { HomeHero } from "@/components/HomeHero";
import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { COPY } from "@/lib/copy";
import type { Archive, EntryListItem } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

const STEPS = [
  { n: "01", text: COPY.home.steps[0], img: "/design/nyanting-caption-362s.jpg" },
  { n: "02", text: COPY.home.steps[1], img: "/design/contoh-overlay-canting.jpg" },
  { n: "03", text: COPY.home.steps[2], img: "/design/macamcanting-canting-100s.jpg" },
];

export default async function Home() {
  const archives: Archive[] = await fetch(`${API}/api/public/archives`, { cache: "no-store" })
    .then((r) => r.json())
    .catch(() => []);

  const lists = await Promise.all(
    archives.map((a) =>
      fetch(`${API}/api/public/archives/${a.slug}/entries`, { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : []))
        .catch(() => [] as EntryListItem[]),
    ),
  );

  const samples: Record<string, EntryListItem | null> = {};
  archives.forEach((a, i) => {
    const list = lists[i] as EntryListItem[];
    samples[a.slug] = list.find((e) => e.keyframe_url || e.crop_url) ?? list[0] ?? null;
  });

  return (
    <>
      <PublicHeader />
      <main>
        <HomeHero archives={archives} samples={samples} />

        {/* How it works */}
        <section className="border-b-2 border-[var(--color-divider)] px-5 py-12 lg:px-10 lg:py-14">
          <h2 className="mb-6 text-[32px] tracking-[-0.02em] lg:text-[40px]">
            {COPY.home.howItWorks}
          </h2>
          <div className="grid grid-cols-1 gap-8 border-t-2 border-[var(--color-divider)] md:grid-cols-3 md:gap-0">
            {STEPS.map((s) => (
              <div
                key={s.n}
                className="flex flex-col gap-3 pt-6 md:border-r md:border-[var(--color-divider)] md:pr-6 md:last:border-r-0"
              >
                <span className="font-heading text-[52px] leading-none text-[var(--color-accent)] lg:text-[56px]">
                  {s.n}
                </span>
                <div className="frame-media aspect-16/9">
                  {/* Original recording frame, never generated. */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={s.img} alt="" className="size-full object-cover" />
                </div>
                <span className="text-[17px] leading-snug lg:text-[18px]">{s.text}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Principles */}
        <section className="grid grid-cols-1 border-b-2 border-[var(--color-divider)] lg:grid-cols-[200px_repeat(4,minmax(0,1fr))]">
          <div className="label px-5 py-6 lg:px-10">{COPY.home.principlesTitle}</div>
          {COPY.home.principles.map((p) => (
            <div
              key={p}
              className="border-t border-[var(--color-divider)] px-5 py-5 text-[16px] font-semibold lg:border-t-0 lg:border-l lg:px-6 lg:py-6 lg:text-[18px]"
            >
              {p}
            </div>
          ))}
        </section>

        {/* Vision */}
        <section
          className="px-5 py-14 lg:px-10 lg:py-[72px]"
          style={{ background: "var(--color-accent)", color: "var(--color-bg)" }}
        >
          <p className="max-w-[1100px] text-[30px] leading-[1.02] font-extrabold tracking-[-0.03em] lg:text-[56px]">
            {COPY.home.vision}
          </p>
        </section>
      </main>
      <PublicFooter />
    </>
  );
}
