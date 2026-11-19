import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSmoothText } from "./useSmoothText";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

const frames = (n: number) => act(() => vi.advanceTimersByTime(16 * n));

describe("useSmoothText", () => {
  it("reveals streamed text gradually, then fully", () => {
    const { result, rerender } = renderHook(({ text, active }) => useSmoothText(text, active), {
      initialProps: { text: "", active: true },
    });
    rerender({ text: "Global Automation leads spend this month.", active: true });

    frames(1);
    const partial = result.current;
    expect(partial.length).toBeGreaterThan(0);
    expect(partial.length).toBeLessThan(41);
    expect("Global Automation leads spend this month.".startsWith(partial)).toBe(true);

    frames(40);
    expect(result.current).toBe("Global Automation leads spend this month.");
  });

  it("catches up quickly when far behind", () => {
    const long = "x".repeat(2000);
    const { result, rerender } = renderHook(({ text }) => useSmoothText(text, true), {
      initialProps: { text: "" },
    });
    rerender({ text: long });
    frames(40); // about two thirds of a second, however big the burst
    expect(result.current).toBe(long);
  });

  it("shows finished messages at once", () => {
    const { result } = renderHook(() => useSmoothText("Loaded from history.", false));
    expect(result.current).toBe("Loaded from history.");
  });

  it("jumps straight to replaced text", () => {
    const { result, rerender } = renderHook(({ text }) => useSmoothText(text, true), {
      initialProps: { text: "Spend is 999." },
    });
    frames(40);
    rerender({ text: "Spend is 120." });
    expect(result.current).toBe("Spend is 120.");
  });

  it("finishes the reveal after the stream ends", () => {
    const { result, rerender } = renderHook(({ text, active }) => useSmoothText(text, active), {
      initialProps: { text: "", active: true },
    });
    rerender({ text: "Two vendors are late.", active: false });
    frames(40);
    expect(result.current).toBe("Two vendors are late.");
  });
});
