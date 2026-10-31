import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { UploadForm } from "@/components/UploadForm";

export default function TryPage() {
  return (
    <>
      <PublicHeader />
      <main className="pb-24">
        <UploadForm variant="try" />
      </main>
      <PublicFooter />
    </>
  );
}
