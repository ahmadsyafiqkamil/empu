import { StudioHome } from "@/components/StudioHome";
import { StudioKeyGate } from "@/components/StudioKeyGate";

export default function StudioPage() {
  return (
    <StudioKeyGate>
      <StudioHome />
    </StudioKeyGate>
  );
}
