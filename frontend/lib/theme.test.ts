import { afterEach, describe, expect, it, vi } from "vitest";
import { applyTheme, readTheme, resolveTheme, saveTheme, THEME_KEY } from "./theme";

afterEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  vi.restoreAllMocks();
});

describe("theme", () => {
  it("resolves system to the OS preference", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
    expect(resolveTheme("light", true)).toBe("light");
  });

  it("saves and reads the choice, defaulting to system", () => {
    expect(readTheme()).toBe("system");
    saveTheme("dark");
    expect(localStorage.getItem(THEME_KEY)).toBe("dark");
    expect(readTheme()).toBe("dark");
  });

  it("ignores unknown stored values", () => {
    localStorage.setItem(THEME_KEY, "purple");
    expect(readTheme()).toBe("system");
  });

  it("survives storage that throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(readTheme()).toBe("system");
    expect(() => saveTheme("dark")).not.toThrow();
  });

  it("applies the resolved theme to the document", () => {
    applyTheme("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    applyTheme("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
