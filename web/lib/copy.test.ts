import { describe, expect, it } from "vitest";
import { ensureTrimmedByEmpu } from "./copy";

describe("ensureTrimmedByEmpu", () => {
  it("appends the trim note once when the API omits it", () => {
    expect(ensureTrimmedByEmpu('From "X" by Y · CC BY 3.0')).toBe(
      'From "X" by Y · CC BY 3.0 · Trimmed by Empu',
    );
  });

  it("does not stack a second trim note", () => {
    expect(ensureTrimmedByEmpu("From X · Trimmed by Empu")).toBe("From X · Trimmed by Empu");
    expect(ensureTrimmedByEmpu("From X · Trimmed and analyzed by Empu.")).toBe(
      "From X · Trimmed and analyzed by Empu.",
    );
  });
});
