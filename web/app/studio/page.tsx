import Link from "next/link";
import { StudioKeyGate } from "@/components/StudioKeyGate";

export default function StudioHome() {
  return (
    <StudioKeyGate>
      <main className="p-8">
        <p className="text-sm tracking-wide text-[var(--muted)]">EMPU · BATIK TULIS</p>
        <h1 className="mt-2 text-3xl">Studio</h1>
        <div className="mt-8 flex gap-4">
          <Link className="border border-[var(--line)] px-4 py-3" href="/studio/upload">
            Upload recording
          </Link>
        </div>
      </main>
    </StudioKeyGate>
  );
}
