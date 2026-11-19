import { Fragment, type ReactNode } from "react";

/** `**bold**` inside a line. Unfinished markers (mid-stream) stay as plain text. */
function inline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    /^\*\*[^*]+\*\*$/.test(part) ? (
      <strong key={i} className="font-semibold text-ink">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  );
}

/**
 * Minimal, safe rendering for assistant answers: paragraphs, "- " bullet lists and bold.
 * No HTML is ever interpreted.
 */
export function RichText({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/);
  return (
    <>
      {blocks.map((block, b) => {
        const lines = block.split("\n");
        const bullets = lines.filter((l) => /^\s*[-•]\s+/.test(l));
        if (bullets.length > 0 && bullets.length === lines.filter((l) => l.trim()).length - (lines[0] && !/^\s*[-•]\s+/.test(lines[0]) ? 1 : 0)) {
          const lead = /^\s*[-•]\s+/.test(lines[0] ?? "") ? null : lines[0];
          return (
            <Fragment key={b}>
              {lead && <p className="leading-relaxed">{inline(lead)}</p>}
              <ul className="ml-4 list-disc space-y-0.5 marker:text-muted">
                {bullets.map((line, i) => (
                  <li key={i}>{inline(line.replace(/^\s*[-•]\s+/, ""))}</li>
                ))}
              </ul>
            </Fragment>
          );
        }
        return (
          <p key={b} className="whitespace-pre-wrap leading-relaxed">
            {inline(block)}
          </p>
        );
      })}
    </>
  );
}
