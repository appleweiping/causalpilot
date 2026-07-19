import { describe, expect, it } from "vitest";
import { normalizeEpisodeSnapshot } from "./client";

describe("normalizeEpisodeSnapshot", () => {
  it("unwraps API envelopes and preserves backend fields", () => {
    const result = normalizeEpisodeSnapshot(
      {
        data: {
          mission_id: "live-7",
          state: "PROBING",
          metrics: { exposures: 1234, uplift: 0.019 },
          risks: { causal: { score: 0.31, evidence: ["RCT active"] } },
          segments: [{ id: "vip", label: "VIP", coordinates: { x: 1, y: 2, z: 3 } }],
        },
      },
      2,
    );
    expect(result.mission_id).toBe("live-7");
    expect(result.metrics.exposures).toBe(1234);
    expect(result.metrics.uplift).toBe(0.019);
    expect(result.risks.causal.level).toBe("guarded");
    expect(result.segments[0].coordinates).toEqual([1, 2, 3]);
  });

  it("fills every missing field from a deterministic phase snapshot", () => {
    const result = normalizeEpisodeSnapshot({ mission_id: "partial" }, 4);
    expect(result.mission_id).toBe("partial");
    expect(result.pending_question).toContain("margin floor and first-order subsidy cap");
    expect(result.metrics.exposures).toBe(19600);
    expect(result.segments).toHaveLength(4);
  });
});
