import { describe, expect, it } from "vitest";
import { compactNumber } from "./format";

describe("compactNumber", () => {
  it.each([
    [0, "0"],
    [950, "950"],
    [1500, "1.5K"],
    [4_500_000, "45L"],
    [15_000_000, "1.5Cr"],
    [-3_000_000, "-30L"],
  ])("formats %d as %s", (value, expected) => {
    expect(compactNumber(value)).toBe(expected);
  });

  it("passes non-numbers through", () => {
    expect(compactNumber("placed")).toBe("placed");
  });
});
