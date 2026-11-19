export type SqlTokenKind = "keyword" | "string" | "number" | "text";

export interface SqlToken {
  kind: SqlTokenKind;
  text: string;
}

const KEYWORDS = new Set(
  (
    "select from where and or not in is null as on join left right inner outer full cross " +
    "group by order having limit offset with distinct case when then else end union all " +
    "asc desc between like ilike exists coalesce nullif cast interval count sum avg min max " +
    "true false over partition filter"
  ).split(" "),
);

const PATTERN = /('(?:[^']|'')*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|([\s\S])/g;

/** Splits SQL into tokens for display. Joining the token texts gives back the input exactly. */
export function tokenizeSql(sql: string): SqlToken[] {
  const tokens: SqlToken[] = [];
  const push = (kind: SqlTokenKind, text: string) => {
    const last = tokens.at(-1);
    if (kind === "text" && last?.kind === "text") last.text += text;
    else tokens.push({ kind, text });
  };
  for (const [, str, num, word, other] of sql.matchAll(PATTERN)) {
    if (str) push("string", str);
    else if (num) push("number", num);
    else if (word) push(KEYWORDS.has(word.toLowerCase()) ? "keyword" : "text", word);
    else push("text", other);
  }
  return tokens;
}
