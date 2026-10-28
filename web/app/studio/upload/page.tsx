import { StudioKeyGate } from "@/components/StudioKeyGate";
import { UploadForm } from "@/components/UploadForm";

export default function UploadPage() {
  return (
    <StudioKeyGate>
      <UploadForm />
    </StudioKeyGate>
  );
}
