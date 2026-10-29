import { JobProgress } from "@/components/JobProgress";
import { StudioKeyGate } from "@/components/StudioKeyGate";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  // Sandbox jobs are readable without a studio key so the judge can watch their
  // own 3-minute clip. Probe the job once without a key: if it resolves, render
  // progress directly; otherwise fall through to the studio-key gate.
  let isSandbox = false;
  try {
    const r = await fetch(`${API}/api/jobs/${id}`, { cache: "no-store" });
    isSandbox = r.ok;
  } catch {
    isSandbox = false;
  }

  if (isSandbox) {
    return <JobProgress jobId={id} />;
  }
  return (
    <StudioKeyGate>
      <JobProgress jobId={id} />
    </StudioKeyGate>
  );
}