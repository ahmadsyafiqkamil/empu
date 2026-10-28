import { describe, expect, it } from "vitest";
import { STAGE_LABEL } from "./copy";

describe("STAGE_LABEL", () => {
  it("maps pipeline stages to COPY labels verbatim", () => {
    expect(STAGE_LABEL.normalizing).toBe("Preparing video");
    expect(STAGE_LABEL.analyzing).toBe("Muse Spark watches and listens");
    expect(STAGE_LABEL.ready).toBe("Ready to review");
  });
});
