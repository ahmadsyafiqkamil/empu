"use client";

import { Volume2 } from "lucide-react";
import { useRef, useState } from "react";

export function PronounceButton({ audioUrl }: { audioUrl: string | null }) {
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
        className="inline-flex items-center justify-center rounded-[var(--radius)] p-1 text-[var(--accent)] outline-[var(--wax)]"
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
        <Volume2 className="size-4" aria-hidden />
      </button>
    </>
  );
}
