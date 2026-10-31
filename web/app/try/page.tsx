import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { UploadForm } from "@/components/UploadForm";

export default function TryPage() {
  return (
    <>
      <PublicHeader />
      <main>
        <UploadForm variant="try" />
      </main>
      <PublicFooter />
    </>
  );
}
