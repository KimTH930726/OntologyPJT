import { useMemo } from "react";

export default function ChunkViewer({
  text,
  highlights,
}: {
  text: string;
  highlights?: string[];
}) {
  const parts = useMemo(() => splitByHighlights(text, highlights ?? []), [text, highlights]);
  return (
    <div className="whitespace-pre-wrap break-words rounded-md border border-slate-200 bg-white p-4 text-sm leading-7 text-slate-800">
      {parts.map((p, i) =>
        p.hit ? (
          <mark
            key={i}
            className="rounded bg-amber-200/70 px-0.5 text-slate-900"
          >
            {p.text}
          </mark>
        ) : (
          <span key={i}>{p.text}</span>
        ),
      )}
    </div>
  );
}

function splitByHighlights(text: string, terms: string[]): { text: string; hit: boolean }[] {
  const valid = terms.map((t) => t.trim()).filter((t) => t.length > 0);
  if (valid.length === 0) return [{ text, hit: false }];
  const pattern = new RegExp(
    "(" + valid.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")",
    "gi",
  );
  const out: { text: string; hit: boolean }[] = [];
  let last = 0;
  for (const m of text.matchAll(pattern)) {
    const idx = m.index ?? 0;
    if (idx > last) out.push({ text: text.slice(last, idx), hit: false });
    out.push({ text: m[0], hit: true });
    last = idx + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last), hit: false });
  return out;
}
