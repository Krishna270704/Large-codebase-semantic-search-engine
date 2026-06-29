import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

/* ── Language map ──────────────────────────────────────────────── */
const LANG_MAP = {
  py: "python",
  js: "javascript",
  ts: "typescript",
  jsx: "jsx",
  tsx: "tsx",
  java: "java",
  cpp: "cpp",
  c: "c",
  cs: "csharp",
  go: "go",
  rs: "rust",
  rb: "ruby",
  php: "php",
  swift: "swift",
  kt: "kotlin",
  md: "markdown",
  json: "json",
  yaml: "yaml",
  yml: "yaml",
  xml: "xml",
  html: "html",
  css: "css",
  sql: "sql",
  sh: "bash",
  bash: "bash",
  txt: "text",
};

function resolveLang(language, filePath) {
  if (language && LANG_MAP[language]) return LANG_MAP[language];
  if (language && language !== "unknown") return language;
  // Fallback: guess from extension
  const ext = filePath?.split(".").pop()?.toLowerCase();
  return LANG_MAP[ext] || "text";
}

/**
 * ResultCard – renders a single search hit with syntax-highlighted code.
 *
 * @param {object} props
 * @param {object} props.result       A SearchResultItem from the backend.
 * @param {number} props.rank         1-based rank in the list.
 */
export default function ResultCard({ result, rank }) {
  const [expanded, setExpanded] = useState(true);
  const lang = resolveLang(result.language, result.file_path);
  const score = (result.score * 100).toFixed(1);

  // Color for similarity badge
  const badgeColor =
    result.score >= 0.8
      ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20"
      : result.score >= 0.5
        ? "text-amber-400 bg-amber-400/10 border-amber-400/20"
        : "text-red-400 bg-red-400/10 border-red-400/20";

  return (
    <div className="glass-card group animate-slide-up overflow-hidden transition-all duration-300 hover:border-white/10">
      {/* Header */}
      <button
        onClick={() => setExpanded((p) => !p)}
        className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-white/[0.02]"
      >
        {/* Rank badge */}
        <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-brand-600/20 text-xs font-bold text-brand-300">
          {rank}
        </span>

        {/* File path */}
        <div className="min-w-0 flex-1">
          <p className="truncate font-mono text-sm font-medium text-white/90">
            {result.file_path}
          </p>
          <p className="mt-0.5 text-xs text-white/35">
            Lines {result.start_line}–{result.end_line} ·{" "}
            <span className="uppercase">{lang}</span>
          </p>
        </div>

        {/* Score badge */}
        <span
          className={`flex-shrink-0 rounded-lg border px-2.5 py-1 text-xs font-semibold ${badgeColor}`}
        >
          {score}%
        </span>

        {/* Expand/collapse chevron */}
        <svg
          className={`h-4 w-4 flex-shrink-0 text-white/30 transition-transform duration-200 ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Code snippet */}
      {expanded && (
        <div className="border-t border-white/[0.04] text-sm">
          <SyntaxHighlighter
            language={lang}
            style={oneDark}
            showLineNumbers
            startingLineNumber={result.start_line}
            wrapLongLines
            customStyle={{
              margin: 0,
              padding: "1rem 1.25rem",
              background: "transparent",
              fontSize: "0.82rem",
              lineHeight: "1.6",
            }}
            lineNumberStyle={{
              minWidth: "2.5em",
              paddingRight: "1em",
              color: "rgba(255,255,255,0.15)",
              userSelect: "none",
            }}
          >
            {result.snippet}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
}
