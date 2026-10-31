import { describe, expect, it } from "vitest";
import {
  archiveSlugFromPathname,
  isTypingTarget,
  pickArchiveSlug,
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

describe("archiveSlugFromPathname", () => {
  it("reads the archive slug from a nested path", () => {
    expect(archiveSlugFromPathname("/d/batik-tulis")).toBe("batik-tulis");
    expect(archiveSlugFromPathname("/d/batik-tulis/12")).toBe("batik-tulis");
    expect(archiveSlugFromPathname("/d/batik-tulis/12/map/3")).toBe("batik-tulis");
  });

  it("ignores paths that are not dictionaries", () => {
    expect(archiveSlugFromPathname("/")).toBeNull();
    expect(archiveSlugFromPathname("/map")).toBeNull();
    expect(archiveSlugFromPathname("/studio")).toBeNull();
    expect(archiveSlugFromPathname("/dx/batik-tulis")).toBeNull();
  });
});

describe("pickArchiveSlug", () => {
  it("prefers the demo archive and skips sandboxes", () => {
    expect(
      pickArchiveSlug([
        { slug: "sandbox", is_sandbox: true },
        { slug: "gamelan", is_demo: false },
        { slug: "batik-tulis", is_demo: true },
      ]),
    ).toBe("batik-tulis");
  });

  it("falls back to the first non-sandbox archive", () => {
    expect(
      pickArchiveSlug([
        { slug: "sandbox", is_sandbox: true },
        { slug: "gamelan", is_demo: false },
      ]),
    ).toBe("gamelan");
  });

  it("returns null when there is nothing to ask", () => {
    expect(pickArchiveSlug([])).toBeNull();
    expect(pickArchiveSlug([{ slug: "sandbox", is_sandbox: true }])).toBeNull();
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
