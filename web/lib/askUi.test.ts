import { describe, expect, it } from "vitest";
import {
  isTypingTarget,
  shouldCloseOnHide,
  shouldShowLauncher,
  termQuestion,
} from "./askUi";

describe("shouldShowLauncher", () => {
  it("hides the launcher on studio and ask routes", () => {
    expect(shouldShowLauncher("/studio")).toBe(false);
    expect(shouldShowLauncher("/studio/upload")).toBe(false);
    expect(shouldShowLauncher("/studio/recordings/7")).toBe(false);
    expect(shouldShowLauncher("/studio/ask")).toBe(false);
    expect(shouldShowLauncher("/ask")).toBe(false);
    expect(shouldShowLauncher("/d/batik-tulis/ask")).toBe(false);
  });

  it("shows the launcher on public routes", () => {
    expect(shouldShowLauncher("/")).toBe(true);
    expect(shouldShowLauncher("/d/batik-tulis")).toBe(true);
    expect(shouldShowLauncher("/d/batik-tulis/1")).toBe(true);
    expect(shouldShowLauncher("/map")).toBe(true);
    expect(shouldShowLauncher("/evidence")).toBe(true);
    expect(shouldShowLauncher("/try")).toBe(true);
  });
});

describe("termQuestion", () => {
  it("formats a term question", () => {
    expect(termQuestion("canting")).toBe("What is canting?");
    expect(termQuestion("  canting  ")).toBe("What is canting?");
  });
});

describe("shouldCloseOnHide", () => {
  it("closes the sheet when the launcher is no longer shown", () => {
    expect(shouldCloseOnHide(false, true)).toBe(true);
    expect(shouldCloseOnHide(false, false)).toBe(false);
    expect(shouldCloseOnHide(true, true)).toBe(false);
    expect(shouldCloseOnHide(true, false)).toBe(false);
  });
});

describe("isTypingTarget", () => {
  it("does not steal the shortcut from a text field", () => {
    expect(isTypingTarget("INPUT")).toBe(true);
    expect(isTypingTarget("textarea")).toBe(true);
    expect(isTypingTarget("SELECT")).toBe(true);
    expect(isTypingTarget("DIV")).toBe(false);
    expect(isTypingTarget(null)).toBe(false);
    expect(isTypingTarget(undefined)).toBe(false);
  });
});
