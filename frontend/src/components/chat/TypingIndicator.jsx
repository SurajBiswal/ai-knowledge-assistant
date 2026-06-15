/**
 * TypingIndicator
 * Shows an animated "assistant is thinking" bubble.
 * Usage: <TypingIndicator />
 */
export default function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 group">
      {/* Assistant avatar */}
      <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center flex-shrink-0 shadow-sm">
        <svg
          className="w-4 h-4 text-indigo-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
          />
        </svg>
      </div>

      {/* Bubble */}
      <div className="flex flex-col items-start gap-1">
        <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-3.5 shadow-sm flex items-center gap-1.5">
          <span
            className="w-2 h-2 bg-slate-300 rounded-full animate-bounce"
            style={{ animationDelay: "0ms", animationDuration: "900ms" }}
          />
          <span
            className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
            style={{ animationDelay: "160ms", animationDuration: "900ms" }}
          />
          <span
            className="w-2 h-2 bg-slate-500 rounded-full animate-bounce"
            style={{ animationDelay: "320ms", animationDuration: "900ms" }}
          />
        </div>
        <span className="text-[11px] text-slate-400 px-1">KnowledgeAI is thinking…</span>
      </div>
    </div>
  );
}
