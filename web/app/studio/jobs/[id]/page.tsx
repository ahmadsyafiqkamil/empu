import { JobProgress } from "@/components/JobProgress";
import { StudioKeyGate } from "@/components/StudioKeyGate";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <StudioKeyGate>
      <JobProgress jobId={id} />
    </StudioKeyGate>
  );
}
