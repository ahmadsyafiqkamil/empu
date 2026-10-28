"use client";

import { useState } from "react";
import { COPY } from "@/lib/copy";

export function CropView({
  cropUrl,
  overlayUrl,
  keyframeUrl,
  samStatus,
}: {
  cropUrl: string | null;
  overlayUrl: string | null;
  keyframeUrl: string | null;
  samStatus: string;
}) {
  const [showInFrame, setShowInFrame] = useState(false);
  const cropOk = samStatus === "ok" && Boolean(cropUrl);
  const src = cropOk
    ? showInFrame && overlayUrl
      ? overlayUrl
      : cropUrl
    : keyframeUrl;
  const label = cropOk ? COPY.crop.original : COPY.crop.noCrop;
  return (
    <div className="space-y-2">
      <div className="aspect-[4/5] overflow-hidden bg-[var(--surface)]">
        {src ? (
          // Frame URLs only — original recording stills, never generated images.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={label} className="h-full w-full object-contain" />
        ) : (
          <div className="flex h-full items-center justify-center p-3 text-center text-xs text-[var(--muted)]">
            {COPY.crop.noCrop}
          </div>
        )}
      </div>
      <div className="flex items-center justify-between gap-2 text-xs text-[var(--muted)]">
        <span>{label}</span>
        {cropOk && overlayUrl ? (
          <label className="inline-flex cursor-pointer items-center gap-1.5">
            <input
              type="checkbox"
              checked={showInFrame}
              onChange={(e) => setShowInFrame(e.target.checked)}
            />
            {COPY.crop.showInFrame}
          </label>
        ) : null}
      </div>
    </div>
  );
}
