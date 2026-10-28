import { COPY } from "./copy";
import type { Source } from "./types";

export function sourceLabel(source: Source): string {
  switch (source) {
    case "speech":
      return COPY.source.speech;
    case "on_screen_text":
      return COPY.source.on_screen_text;
    case "visual_only":
      return COPY.source.visual_only;
    default: {
      const _exhaustive: never = source;
      return _exhaustive;
    }
  }
}

export function sourceTooltip(source: Source): string {
  switch (source) {
    case "speech":
      return COPY.sourceTooltip.speech;
    case "on_screen_text":
      return COPY.sourceTooltip.on_screen_text;
    case "visual_only":
      return COPY.sourceTooltip.visual_only;
    default: {
      const _exhaustive: never = source;
      return _exhaustive;
    }
  }
}

export function sourceColorVar(source: Source): string {
  switch (source) {
    case "speech":
      return "var(--src-speech)";
    case "on_screen_text":
      return "var(--src-onscreen)";
    case "visual_only":
      return "var(--src-visual)";
    default: {
      const _exhaustive: never = source;
      return _exhaustive;
    }
  }
}

export function timeSourceLabel(timeSource: "asr" | "muse"): string {
  switch (timeSource) {
    case "asr":
      return COPY.timeSource.asr;
    case "muse":
      return COPY.timeSource.muse;
    default: {
      const _exhaustive: never = timeSource;
      return _exhaustive;
    }
  }
}

export function timeSourceTooltip(timeSource: "asr" | "muse"): string {
  switch (timeSource) {
    case "asr":
      return COPY.timeSourceTooltip.asr;
    case "muse":
      return COPY.timeSourceTooltip.muse;
    default: {
      const _exhaustive: never = timeSource;
      return _exhaustive;
    }
  }
}
