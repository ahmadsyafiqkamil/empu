import { Studio } from "@/components/Studio";
import { StudioKeyGate } from "@/components/StudioKeyGate";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <StudioKeyGate>
      <Studio recordingId={id} />
    </StudioKeyGate>
  );
}
