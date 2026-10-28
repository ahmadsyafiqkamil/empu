import Link from "next/link";
import { COPY } from "@/lib/copy";

export default function Home() {
  return (
    <main className="mx-auto max-w-xl p-8">
      <p className="font-display text-3xl">empu</p>
      <p className="mt-2 text-[var(--muted)]">{COPY.tagline}</p>
      <p className="mt-6">
        <Link href="/studio">Documenter studio →</Link>
      </p>
    </main>
  );
}
