import { describe, expect, it } from "vitest";
import { askErrorCopy, askSuggestions, askSuggestionsAcross, isAskable, normalizeQuestion } from "./ask";
import type { AskEvidence, AskAnswer } from "./types";
import { COPY } from "./copy";

describe("normalizeQuestion", () => {
  it("collapses whitespace and trims", () => {
    expect(normalizeQuestion("  apa   itu\tcanting?  ")).toBe("apa itu canting?");
  });
});

describe("isAskable", () => {
  it("rejects fewer than three characters", () => {
    expect(isAskable("ab")).toBe(false);
    expect(isAskable("abc")).toBe(true);
  });

  it("rejects more than 500 characters", () => {
    expect(isAskable("x".repeat(500))).toBe(true);
    expect(isAskable("x".repeat(501))).toBe(false);
  });

  it("rejects whitespace that normalises down to nothing", () => {
    expect(isAskable("    ")).toBe(false);
  });
});

describe("askSuggestions", () => {
  it("builds unique suggestions capped at n", () => {
    const entries = [{ term: "canting" }, { term: "canting" }, { term: "nglorod" }];
    expect(askSuggestions(entries, 2)).toEqual(["What is canting?", "What is nglorod?"]);
  });

  it("returns an empty list for an empty archive", () => {
    expect(askSuggestions([])).toEqual([]);
  });
});

describe("askSuggestionsAcross", () => {
  it("takes one suggestion per archive before repeating one", () => {
    expect(
      askSuggestionsAcross(
        [
          { title: "Batik", terms: ["canting", "mori"] },
          { title: "Gamelan", terms: ["saron"] },
        ],
        3,
      ),
    ).toEqual(["What is canting?", "What is saron?", "What is mori?"]);
  });

  it("skips blank terms and returns nothing when every archive is empty", () => {
    expect(askSuggestionsAcross([{ title: "A", terms: ["  "] }])).toEqual([]);
    expect(askSuggestionsAcross([])).toEqual([]);
  });
});

describe("askErrorCopy", () => {
  it("maps 429 and 502 to their own copy", () => {
    expect(askErrorCopy(429)).toBe(COPY.ask.rateLimited);
    expect(askErrorCopy(502)).toBe(COPY.ask.unavailable);
    expect(askErrorCopy(500)).toBe(COPY.ask.failed);
  });
});

describe("ask answer shape", () => {
  it("keeps the source label on every piece of evidence", () => {
    const evidence: AskEvidence = {
      archive_slug: "hidup-batik",
      archive_title: "Arsip Hidup",
      entry: {
        id: 1,
        term: "canting",
        category: "tool",
        stage_id: null,
        gloss_id: "alat",
        gloss_en: "tool",
        is_novel: false,
        status: "accepted",
        access_level: "public",
        source: "speech",
        confidence: "high",
        n_occurrences: 1,
        crop_url: null,
        keyframe_url: null,
        clip_url: null,
      },
      occurrence: {
        id: 9,
        entry_id: 1,
        recording_id: 1,
        recording_title: "Rekaman",
        spoken: "canting",
        term_raw: "canting",
        source: "speech",
        t_start: 1,
        t_end: 2,
        time_source: "asr",
        stage_id: null,
        visible: "",
        visible_object_en: null,
        visual_match: "yes",
        evidence_quote: "ini namanya canting",
        confidence: "high",
        status: "accepted",
        clip_url: "/media/a.mp4",
        audio_url: null,
        keyframe_url: null,
      },
    };
    const answer: AskAnswer = {
      answer: "Canting adalah alat.",
      lang: "id",
      refused: false,
      evidence: [evidence],
      model: "muse-spark-1.3",
      prompt_version: "ask-v1",
      cached: false,
    };
    expect(answer.evidence[0].occurrence.source).toBe("speech");
  });
});
