"use client";

import { Volume2 } from "lucide-react";
import { useRef, useState } from "react";
import { COPY } from "@/lib/copy";

export function PronounceButton({
  audioUrl,
  className = "",
}: {
  audioUrl: string | null;
  className?: string;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  if (!audioUrl) return null;

  return (
    <>
      <audio
        ref={audioRef}
        src={audioUrl}
        hidden
        onEnded={() => setPlaying(false)}
        onPause={() => setPlaying(false)}
        onPlay={() => setPlaying(true)}
      />
      <button
        type="button"
        className={`btn btn-primary gap-2.5 justify-start px-4 text-[15px] ${className}`}
        style={{ height: 48, minWidth: 150 }}
        aria-label={playing ? "Stop pronunciation" : "Play pronunciation"}
        onClick={() => {
          const el = audioRef.current;
          if (!el) return;
          if (playing) {
            el.pause();
            el.currentTime = 0;
            setPlaying(false);
            return;
          }
          void el.play();
        }}
      >
        <Volume2 className="size-4.5" aria-hidden />
        {playing ? COPY.ui.playing : COPY.ui.hearIt}
      </button>
    </>
  );
}
