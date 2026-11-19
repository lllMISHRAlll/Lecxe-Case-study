import { describe, expect, it } from "vitest";
import { tokenizeSql } from "./highlight";

describe("tokenizeSql", () => {
  it("marks keywords, strings and numbers and keeps the text intact", () => {
    const sql = "SELECT name FROM proc_vendors WHERE city = 'Pune' LIMIT 500";
    const tokens = tokenizeSql(sql);

    expect(tokens.map((t) => t.text).join("")).toBe(sql);
    expect(tokens.filter((t) => t.kind === "keyword").map((t) => t.text)).toEqual([
      "SELECT",
      "FROM",
      "WHERE",
      "LIMIT",
    ]);
    expect(tokens.find((t) => t.kind === "string")?.text).toBe("'Pune'");
    expect(tokens.find((t) => t.kind === "number")?.text).toBe("500");
  });

  it("matches keywords case-insensitively but not inside identifiers", () => {
    const tokens = tokenizeSql("select selected_at from t");
    expect(tokens.filter((t) => t.kind === "keyword").map((t) => t.text)).toEqual(["select", "from"]);
  });
});
