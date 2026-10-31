"use client";

import { useState } from "react";
import { COPY } from "@/lib/copy";

export function CropView({
  cropUrl,
  overlayUrl,
  keyframeUrl,
  samStatus,
  mode = "full",
}: {
  cropUrl: string | null;
  overlayUrl: string | null;
  keyframeUrl: string | null;
  samStatus: string;
  mode?: "full" | "compact";
}) {
  const [showInFrame, setShowInFrame] = useState(false);
  const cropOk = samStatus === "ok" && Boolean(cropUrl);
  const src = cropOk ? (showInFrame && overlayUrl ? overlayUrl : cropUrl) : keyframeUrl;
  const label = cropOk ? COPY.crop.original : COPY.crop.noCrop;

  return (
    <div className="flex flex-col gap-1.5">
      <div
        className={
          cropOk
            ? "grid aspect-4/5 place-items-center overflow-hidden bg-[var(--color-surface)]"
            : "grid aspect-video place-items-center overflow-hidden bg-[var(--color-surface)]"
        }
      >
        {src ? (
          // Frame URL only — original recording stills, never generated images.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={label} className="size-full object-contain" />
        ) : (
          <span className="p-2 text-center text-[11px] text-[var(--color-neutral-700)]">
            {COPY.crop.noCrop}
          </span>
        )}
      </div>

      {cropOk && overlayUrl ? (
        mode === "full" ? (
          <div className="seg w-full">
            <label className="seg-opt flex-1 justify-center text-[11px]">
              <input
                type="radio"
                name={`crop-${cropUrl}`}
                checked={!showInFrame}
                onChange={() => setShowInFrame(false)}
              />
              {COPY.crop.showCrop}
            </label>
            <label className="seg-opt flex-1 justify-center text-[11px]">
              <input
                type="radio"
                name={`crop-${cropUrl}`}
                checked={showInFrame}
                onChange={() => setShowInFrame(true)}
              />
              {COPY.crop.showInFrame}
            </label>
          </div>
        ) : (
          <button
            type="button"
            aria-pressed={showInFrame}
            className="btn btn-secondary h-7 w-full text-[11px]"
            onClick={() => setShowInFrame((v) => !v)}
          >
            {showInFrame ? COPY.crop.showCrop : COPY.crop.showInFrame}
          </button>
        )
      ) : null}

      <p className="text-[11px] leading-snug text-[var(--color-neutral-700)]">{label}</p>
    </div>
  );
}
