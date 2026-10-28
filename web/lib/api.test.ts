import { describe, expect, it } from "vitest";
import { mediaSrc } from "./api";

describe("mediaSrc", () => {
  it("passes through relative media urls", () => {
    expect(mediaSrc("/media/a.mp4")).toBe("/media/a.mp4");
    expect(mediaSrc(null)).toBeUndefined();
  });
});
