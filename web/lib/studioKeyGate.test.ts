import { describe, expect, it } from "vitest";
import { isStudioKeySubmittable, isStudioKeyUnauthorized } from "./studioKeyGate";

describe("isStudioKeySubmittable", () => {
  it("refuses empty and whitespace-only keys", () => {
    expect(isStudioKeySubmittable("")).toBe(false);
    expect(isStudioKeySubmittable("   ")).toBe(false);
  });

  it("accepts non-empty trimmed keys", () => {
    expect(isStudioKeySubmittable("abc")).toBe(true);
    expect(isStudioKeySubmittable("  key  ")).toBe(true);
  });
});

describe("isStudioKeyUnauthorized", () => {
  it("detects 401 from apiGet errors", () => {
    expect(isStudioKeyUnauthorized(new Error("401 Unauthorized"))).toBe(true);
    expect(isStudioKeyUnauthorized(new Error("500 boom"))).toBe(false);
  });
});
