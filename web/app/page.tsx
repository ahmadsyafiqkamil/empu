import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-xl p-8">
      <p className="font-display text-3xl">empu</p>
      <p className="mt-2 text-[var(--muted)]">Capture what masters know, before it's gone.</p>
      <p className="mt-6">
        <Link href="/studio">Documenter studio →</Link>
      </p>
    </main>
  );
}
