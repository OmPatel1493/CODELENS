/**
 * Syntax-highlighted, read-only code snippet.
 *
 * Uses highlight.js (the "common languages" bundle to keep the payload small).
 * We pick the language from the file extension when we can, else auto-detect.
 * The block is always dark-themed for consistent readability in both app themes.
 */

import { useMemo } from "react";
import hljs from "highlight.js/lib/common";
import "highlight.js/styles/github-dark.css";

const EXT_LANG: Record<string, string> = {
  py: "python",
  js: "javascript",
  jsx: "javascript",
  ts: "typescript",
  tsx: "typescript",
  java: "java",
  go: "go",
  rb: "ruby",
  rs: "rust",
  c: "c",
  h: "c",
  cpp: "cpp",
  hpp: "cpp",
  cs: "csharp",
  php: "php",
};

function highlight(code: string, filePath: string): string {
  const ext = filePath.split(".").pop()?.toLowerCase() ?? "";
  const lang = EXT_LANG[ext];
  try {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  } catch {
    return code;
  }
}

export function CodeBlock({ code, filePath }: { code: string; filePath: string }) {
  const html = useMemo(() => highlight(code, filePath), [code, filePath]);
  return (
    <pre className="max-h-80 overflow-auto rounded-md border bg-[#0d1117] p-4 text-sm leading-relaxed">
      <code
        className="hljs bg-transparent p-0 font-mono"
        // highlight.js output is trusted markup generated from our own snippet text.
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </pre>
  );
}
