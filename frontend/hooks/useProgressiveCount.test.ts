import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useProgressiveCount } from "./useProgressiveCount";

describe("useProgressiveCount", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("reveals items one at a time when animating", () => {
    const { result } = renderHook(() => useProgressiveCount(3, { animate: true, intervalMs: 100 }));
    expect(result.current).toBe(1);
    act(() => vi.advanceTimersByTime(100));
    expect(result.current).toBe(2);
    act(() => vi.advanceTimersByTime(100));
    expect(result.current).toBe(3);
    act(() => vi.advanceTimersByTime(500));
    expect(result.current).toBe(3);
  });

  it("keeps revealing items that arrive later", () => {
    const { result, rerender } = renderHook(
      ({ total }) => useProgressiveCount(total, { animate: true, intervalMs: 100 }),
      { initialProps: { total: 1 } },
    );
    expect(result.current).toBe(1);
    rerender({ total: 2 });
    act(() => vi.advanceTimersByTime(100));
    expect(result.current).toBe(2);
  });

  it("shows everything at once when not animating", () => {
    const { result } = renderHook(() => useProgressiveCount(4, { animate: false }));
    expect(result.current).toBe(4);
  });

  it("shows everything at once when the user prefers reduced motion", () => {
    const matchMedia = vi.fn().mockReturnValue({ matches: true });
    vi.stubGlobal("matchMedia", matchMedia);
    const { result } = renderHook(() => useProgressiveCount(4, { animate: true }));
    expect(result.current).toBe(4);
    vi.unstubAllGlobals();
  });

  it("never shows more than there are", () => {
    const { result, rerender } = renderHook(
      ({ total }) => useProgressiveCount(total, { animate: false }),
      { initialProps: { total: 3 } },
    );
    rerender({ total: 1 });
    expect(result.current).toBe(1);
  });
});
