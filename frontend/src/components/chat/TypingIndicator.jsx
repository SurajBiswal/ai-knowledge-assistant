/**
 * TypingIndicator
 * Shows an inline "generating a response…" row while the model is
 * warming up (before the first streamed chunk arrives). Once content
 * starts flowing, the caller stops rendering this in favour of the
 * live-updating MessageBubble.
 * Usage: <TypingIndicator />
 */
export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-2.5 px-1 py-1">
      {/* Small icon avatar */}
      <div className="w-6 h-6 rounded-md bg-ink border border-ink-softer flex items-center justify-center flex-shrink-0">
        <svg className="w-3.5 h-3.5 text-mustard" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
      </div>

      <span className="text-xs text-ink-400 font-mono">generating a response</span>

      <span className="flex items-center gap-1">
        <span className="w-1 h-1 bg-ink-400 rounded-full animate-bounce" style={{ animationDelay: "0ms", animationDuration: "900ms" }} />
        <span className="w-1 h-1 bg-ink-400 rounded-full animate-bounce" style={{ animationDelay: "160ms", animationDuration: "900ms" }} />
        <span className="w-1 h-1 bg-ink-400 rounded-full animate-bounce" style={{ animationDelay: "320ms", animationDuration: "900ms" }} />
      </span>
    </div>
  );
}
