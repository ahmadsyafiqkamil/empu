import { describe, expect, it } from "vitest";
import { sourceLabel } from "./source";

describe("sourceLabel", () => {
  it("uses brief microcopy, not lowercase shorthand", () => {
    expect(sourceLabel("speech")).toBe("Spoken");
    expect(sourceLabel("on_screen_text")).toBe("On-screen text");
    expect(sourceLabel("visual_only")).toBe("Visual only");
  });
});
