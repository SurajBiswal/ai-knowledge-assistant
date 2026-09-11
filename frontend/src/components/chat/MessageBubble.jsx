import { useState } from "react";

/**
 * Lightweight markdown renderer — no external deps required.
 * Handles: bold, italic, inline code, fenced code blocks,
 * headings (##, ###), unordered lists, ordered lists, blockquotes,
 * horizontal rules, and line breaks.
 */
function renderMarkdown(text) {
  const lines = text.split("\n");
  const elements = [];
  let i = 0;
  let keyCounter = 0;
  const key = () => keyCounter++;

  while (i < lines.length) {
    const line = lines[i];

    // ── Fenced code block ────────────────────────────────────────────
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      elements.push(
        <div key={key()} className="my-3 rounded-lg overflow-hidden border border-ink-softer shadow-sm">
          {lang && (
            <div className="flex items-center justify-between px-3 py-1.5 bg-ink border-b border-ink-softer">
              <span className="text-[11px] font-mono font-medium text-paper-400 uppercase tracking-widest">
                {lang}
              </span>
              <CopyButton text={codeLines.join("\n")} />
            </div>
          )}
          <pre className="bg-ink text-paper-100 text-xs font-mono leading-relaxed overflow-x-auto p-4 m-0">
            <code>{codeLines.join("\n")}</code>
          </pre>
        </div>
      );
      i++; // skip closing ```
      continue;
    }

    // ── Blockquote ───────────────────────────────────────────────────
    if (line.startsWith("> ")) {
      elements.push(
        <blockquote
          key={key()}
          className="my-2 pl-3 border-l-4 border-mustard text-ink-600 italic text-sm"
        >
          {inlineMarkdown(line.slice(2))}
        </blockquote>
      );
      i++;
      continue;
    }

    // ── Heading ##  ──────────────────────────────────────────────────
    if (line.startsWith("### ")) {
      elements.push(
        <h3 key={key()} className="font-display text-sm font-semibold text-ink-900 mt-4 mb-1">
          {inlineMarkdown(line.slice(4))}
        </h3>
      );
      i++;
      continue;
    }
    if (line.startsWith("## ")) {
      elements.push(
        <h2 key={key()} className="font-display text-base font-semibold text-ink-900 mt-4 mb-1">
          {inlineMarkdown(line.slice(3))}
        </h2>
      );
      i++;
      continue;
    }

    // ── Horizontal rule ──────────────────────────────────────────────
    if (/^[-*_]{3,}$/.test(line.trim())) {
      elements.push(<hr key={key()} className="my-3 border-paper-line" />);
      i++;
      continue;
    }

    // ── Unordered list ───────────────────────────────────────────────
    if (/^[-*+] /.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*+] /.test(lines[i])) {
        items.push(lines[i].replace(/^[-*+] /, ""));
        i++;
      }
      elements.push(
        <ul key={key()} className="my-2 space-y-1 pl-1">
          {items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-sm">
              <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-moss flex-shrink-0" />
              <span>{inlineMarkdown(item)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // ── Ordered list ─────────────────────────────────────────────────
    if (/^\d+\. /.test(line)) {
      const items = [];
      let num = 1;
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\. /, ""));
        i++;
        num++;
      }
      elements.push(
        <ol key={key()} className="my-2 space-y-1 pl-1">
          {items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2.5 text-sm">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-moss-tint text-moss-dark text-[11px] font-mono font-semibold flex items-center justify-center mt-0.5">
                {idx + 1}
              </span>
              <span>{inlineMarkdown(item)}</span>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // ── Empty line → spacer ──────────────────────────────────────────
    if (line.trim() === "") {
      elements.push(<div key={key()} className="h-2" />);
      i++;
      continue;
    }

    // ── Regular paragraph ────────────────────────────────────────────
    elements.push(
      <p key={key()} className="text-sm leading-relaxed">
        {inlineMarkdown(line)}
      </p>
    );
    i++;
  }

  return elements;
}

/** Processes inline markdown: bold, italic, inline code, links */
function inlineMarkdown(text) {
  // Split on bold (**), italic (*), and inline code (`)
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={idx} className="font-semibold text-ink-900">{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*"))
      return <em key={idx} className="italic">{part.slice(1, -1)}</em>;
    if (part.startsWith("`") && part.endsWith("`"))
      return (
        <code key={idx} className="px-1.5 py-0.5 rounded bg-paper-dim text-moss-dark text-[12px] font-mono border border-paper-line">
          {part.slice(1, -1)}
        </code>
      );
    return part;
  });
}

/** Small copy-to-clipboard button for code blocks */
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (_) {}
  };
  return (
    <button
      onClick={handleCopy}
      className="text-[11px] text-paper-400 hover:text-paper-100 transition-colors duration-150 flex items-center gap-1 font-mono"
    >
      {copied ? (
        <>
          <svg className="w-3.5 h-3.5 text-mustard" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
          Copied
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.637c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
          </svg>
          Copy
        </>
      )}
    </button>
  );
}

/**
 * Sources — the signature element.
 * Each citation reads like a library catalog card: filename, a
 * right-aligned page number, and — when the backend provides one — an
 * italicised excerpt line beneath it.
 */
function Sources({ sources = [] }) {
  if (!sources.length) return null;

  return (
    <div className="mt-3 pt-3" style={{ borderTop: "1px dashed var(--color-paper-line)" }}>
      <div className="flex items-center gap-1.5 mb-2">
        <svg className="w-3.5 h-3.5 text-moss" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
        <span className="text-[11px] font-mono font-semibold uppercase tracking-widest text-ink-400">
          Sources
        </span>
      </div>

      <div className="space-y-1.5">
        {sources.map((source, index) => {
          // Optional excerpt text — accept whichever field name the backend
          // happens to send (excerpt / snippet / quote / text). If none of
          // these are present, the quote line is simply omitted — no schema
          // change required on the backend.
          const excerpt = source.excerpt ?? source.snippet ?? source.quote ?? source.text ?? null;

          return (
            <div
              key={index}
              className="rounded-md border border-paper-line bg-paper-dim/60 px-3 py-2 text-xs"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 font-medium text-ink-900 break-words leading-snug">
                  {source.filename || "Unknown Document"}
                </div>
                {source.page != null && (
                  <span className="flex-shrink-0 text-ink-400 font-mono text-[11px] whitespace-nowrap">
                    page {source.page}
                  </span>
                )}
              </div>
              {excerpt && (
                <p className="mt-1 text-ink-400 italic leading-snug">
                  "{excerpt}"
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Action bar shown below assistant messages on hover */
function AssistantActions({ content }) {
  const [liked, setLiked] = useState(null); // null | 'up' | 'down'
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (_) {}
  };

  return (
    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-150 mt-1.5 ml-1">
      {/* Copy */}
      <button
        onClick={handleCopy}
        title="Copy response"
        className="p-1.5 rounded-md text-ink-400 hover:text-ink-900 hover:bg-paper-dim transition-colors duration-150"
      >
        {copied ? (
          <svg className="w-3.5 h-3.5 text-moss" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.637c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
          </svg>
        )}
      </button>

      {/* Thumbs up */}
      <button
        onClick={() => setLiked(liked === "up" ? null : "up")}
        title="Good response"
        className={`p-1.5 rounded-md transition-colors duration-150 ${
          liked === "up"
            ? "text-moss bg-moss-tint"
            : "text-ink-400 hover:text-ink-900 hover:bg-paper-dim"
        }`}
      >
        <svg className="w-3.5 h-3.5" fill={liked === "up" ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.5c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 012.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V3a.75.75 0 01.75-.75A2.25 2.25 0 0116.5 4.5c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 01-2.649 7.521c-.388.482-.987.729-1.605.729H13.48c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 00-1.423-.23H5.909M14.25 9h2.25M5.909 18.75c.083.205.173.405.27.602.197.4-.078.898-.523.898h-.908c-.889 0-1.713-.518-1.972-1.368a12 12 0 01-.521-3.507c0-1.553.295-3.036.831-4.398C3.387 9.953 4.167 9.5 5 9.5h1.053c.472 0 .745.556.5.96a8.958 8.958 0 00-1.302 4.665c0 1.194.232 2.333.654 3.375z" />
        </svg>
      </button>

      {/* Thumbs down */}
      <button
        onClick={() => setLiked(liked === "down" ? null : "down")}
        title="Poor response"
        className={`p-1.5 rounded-md transition-colors duration-150 ${
          liked === "down"
            ? "text-clay bg-clay-tint"
            : "text-ink-400 hover:text-ink-900 hover:bg-paper-dim"
        }`}
      >
        <svg className="w-3.5 h-3.5" fill={liked === "down" ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 15h2.25m8.024-9.75c.011.05.028.1.052.148.591 1.2.924 2.55.924 3.977a8.96 8.96 0 01-.999 4.125m.023-8.25c-.076-.365.183-.75.575-.75h.908c.889 0 1.713.518 1.972 1.368.339 1.11.521 2.287.521 3.507 0 1.553-.295 3.036-.831 4.398-.306.774-1.086 1.227-1.918 1.227h-1.053c-.472 0-.745-.556-.5-.96a8.95 8.95 0 00.303-.54m.023-8.25H16.48a4.5 4.5 0 01-1.423-.23l-3.114-1.04a4.5 4.5 0 00-1.423-.23H6.504c-.618 0-1.217.247-1.605.729A11.95 11.95 0 002.25 12c0 .434.023.863.068 1.285C2.427 14.306 3.346 15 4.372 15h3.126c.618 0 .991.724.725 1.282A7.471 7.471 0 007.5 19.5a2.25 2.25 0 002.25 2.25.75.75 0 00.75-.75v-.633c0-.573.11-1.14.322-1.672.304-.76.93-1.33 1.653-1.715a9.04 9.04 0 002.861-2.4c.498-.634 1.226-1.08 2.032-1.08h.384" />
        </svg>
      </button>

      {/* Regenerate */}
      <button
        title="Regenerate response"
        className="p-1.5 rounded-md text-ink-400 hover:text-ink-900 hover:bg-paper-dim transition-colors duration-150"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
        </svg>
      </button>
    </div>
  );
}

/**
 * MessageBubble
 * Props:
 *   message: { id, role: 'user'|'assistant', content: string, time?: string, avatar?: string }
 */
export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-end gap-3 group ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold shadow-sm font-mono
          ${isUser
            ? "bg-moss text-paper-100"
            : "bg-ink text-mustard border border-ink-softer"
          }`}
      >
        {isUser ? (
          <span>{message.avatar ?? "JD"}</span>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        )}
      </div>

      {/* Bubble + meta */}
      <div className={`flex flex-col gap-1 max-w-[78%] sm:max-w-[70%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Bubble */}
        <div
          className={`px-4 py-3 shadow-sm
            ${isUser
              ? "bg-ink text-paper-100 rounded-2xl rounded-br-sm"
              : "bg-surface border border-paper-line text-ink-900 rounded-2xl rounded-bl-sm"
            }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          ) : (
            <>
              <div className="prose-sm max-w-none">
                {renderMarkdown(message.content)}
              </div>

              <Sources sources={message.sources} />
            </>
          )}
        </div>

        {/* Timestamp */}
        {message.time && (
          <span className={`text-[11px] text-ink-400 font-mono px-1 ${isUser ? "text-right" : "text-left"}`}>
            {message.time}
          </span>
        )}

        {/* Assistant actions (copy / thumbs / regenerate) */}
        {!isUser && <AssistantActions content={message.content} />}
      </div>
    </div>
  );
}
