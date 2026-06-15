import { useState, useRef, useEffect, useCallback } from "react";

/**
 * ChatInput
 *
 * Props:
 *   onSend(message: string) – called when the user submits
 *   isLoading?  – boolean  – shows spinner, disables send
 *   disabled?   – boolean  – fully disables input + button
 *   placeholder? – string
 *   maxLength?  – number   – character cap (default 4000)
 */
export default function ChatInput({
  onSend,
  isLoading = false,
  disabled = false,
  placeholder = "Ask anything… (Enter to send, Shift+Enter for new line)",
  maxLength = 4000,
}) {
  const [value, setValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef(null);

  const isBlocked = disabled || isLoading;
  const canSend = value.trim().length > 0 && !isBlocked;
  const charCount = value.length;
  const nearLimit = charCount >= maxLength * 0.85;

  // Auto-resize textarea height
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isBlocked) return;
    onSend?.(trimmed);
    setValue("");
    // Reset height
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }, [value, isBlocked, onSend]);

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleChange(e) {
    if (e.target.value.length <= maxLength) setValue(e.target.value);
  }

  // Re-focus textarea after send
  useEffect(() => {
    if (!isLoading && textareaRef.current) textareaRef.current.focus();
  }, [isLoading]);

  return (
    <div className="w-full px-3 sm:px-4 pb-4 pt-2 bg-white">
      <div className="max-w-2xl mx-auto flex flex-col gap-1.5">

        {/* ── Input shell ─────────────────────────────────────────────── */}
        <div
          className={`
            relative flex items-end gap-2 rounded-2xl border px-3 py-2.5 shadow-sm
            transition-all duration-200
            ${disabled
              ? "bg-slate-50 border-slate-200 opacity-60 cursor-not-allowed"
              : isFocused
                ? "bg-white border-indigo-400 ring-2 ring-indigo-100"
                : "bg-slate-50 border-slate-200 hover:border-slate-300"
            }
          `}
        >
          {/* Attach button */}
          <button
            type="button"
            disabled={isBlocked}
            title="Attach file"
            className={`
              flex-shrink-0 mb-0.5 p-1.5 rounded-lg transition-colors duration-150
              ${isBlocked
                ? "text-slate-300 cursor-not-allowed"
                : "text-slate-400 hover:text-indigo-600 hover:bg-indigo-50"
              }
            `}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
            </svg>
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            disabled={isBlocked}
            placeholder={placeholder}
            aria-label="Chat message input"
            className={`
              flex-1 resize-none bg-transparent outline-none text-sm leading-relaxed
              text-slate-900 placeholder-slate-400
              min-h-[24px] max-h-[200px] overflow-y-auto
              transition-colors duration-150
              ${isBlocked ? "cursor-not-allowed" : ""}
            `}
            style={{ scrollbarWidth: "thin" }}
          />

          {/* Send button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={!canSend}
            title={isLoading ? "Waiting for response…" : "Send message"}
            className={`
              flex-shrink-0 mb-0.5 w-8 h-8 rounded-xl flex items-center justify-center
              transition-all duration-200
              ${canSend
                ? "bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white shadow-sm shadow-indigo-200"
                : isLoading
                  ? "bg-indigo-100 text-indigo-400 cursor-not-allowed"
                  : "bg-slate-100 text-slate-400 cursor-not-allowed"
              }
            `}
          >
            {isLoading ? <Spinner /> : <SendIcon />}
          </button>
        </div>

        {/* ── Footer row ──────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-1">
          <p className="text-[11px] text-slate-400 hidden sm:block select-none">
            {isLoading
              ? "Generating response…"
              : "Enter to send · Shift+Enter for new line"}
          </p>

          {/* Character counter — only visible near limit */}
          <span
            className={`
              text-[11px] ml-auto transition-colors duration-150
              ${nearLimit
                ? charCount >= maxLength ? "text-rose-500 font-medium" : "text-amber-500"
                : "text-slate-300"
              }
            `}
          >
            {nearLimit && `${charCount} / ${maxLength}`}
          </span>
        </div>

      </div>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────────────────── */

function SendIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      className="w-4 h-4 animate-spin"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={3} />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
