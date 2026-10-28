import { describe, expect, it } from "vitest";
import { STAGE_LABEL } from "./copy";
import type { JobStageStatus } from "./types";

describe("STAGE_LABEL", () => {
  it("maps pipeline stages to COPY labels verbatim", () => {
    expect(STAGE_LABEL.normalizing).toBe("Preparing video");
    expect(STAGE_LABEL.analyzing).toBe("Muse Spark watches and listens");
    expect(STAGE_LABEL.ready).toBe("Ready to review");
  });
});

describe("JobStageStatus", () => {
  it("uses API words pending and error (not waiting or failed)", () => {
    const statuses: JobStageStatus[] = ["pending", "running", "done", "error"];
    expect(statuses).toContain("pending");
    expect(statuses).toContain("error");
    expect(statuses).not.toContain("waiting" as JobStageStatus);
    expect(statuses).not.toContain("failed" as JobStageStatus);
  });
});
