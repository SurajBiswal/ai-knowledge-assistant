import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import Mark from "../layout/Mark";

/** Plain centered date divider between message groups */
function DateDivider({ label }) {
  return (
    <div className="flex justify-center my-2">
      <span className="text-[11px] font-mono font-medium text-ink-400 tracking-wide select-none">
        {label}
      </span>
    </div>
  );
}

/** Floating scroll-to-bottom button */
function ScrollButton({ onClick, visible }) {
  return (
    <button
      onClick={onClick}
      aria-label="Scroll to bottom"
      className={`absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-3 py-1.5 rounded-full
        bg-paper border border-paper-line shadow-md text-xs font-medium text-ink-600
        hover:border-moss hover:text-moss transition-all duration-200
        ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2 pointer-events-none"}`}
    >
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
      </svg>
      Jump to latest
    </button>
  );
}

/**
 * ChatWindow
 *
 * Props:
 *   messages     – array of message objects from parent state (required)
 *   isLoading?   – boolean, shows TypingIndicator while waiting for a response
 *   className?   – extra classes for the outer wrapper
 *
 * Each message: { id, role: 'user'|'assistant', content, time?, date? }
 * Date is optional; a divider is rendered whenever it changes.
 */
export default function ChatWindow({
  messages = [],
  isLoading = false,
  className = "",
}) {
  const bottomRef = useRef(null);
  const scrollRef = useRef(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  // Auto-scroll to bottom on new messages / loading change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Show scroll-to-bottom button when user scrolls up
  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBtn(distFromBottom > 120);
  }

  function scrollToBottom() {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  // Group messages by date label
  let lastDate = null;

  return (
    <div className={`relative flex flex-col flex-1 min-h-0 bg-paper ${className}`}>
      {/* Scrollable message list */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto scroll-smooth"
      >
        {/* Top padding + max-width centering */}
        <div className="max-w-2xl mx-auto px-4 pt-6 pb-4 flex flex-col gap-5">
          {/* Empty state */}
          {messages.length === 0 && !isLoading && (
            <div className="flex flex-col items-center justify-center py-24 gap-3 text-center select-none">
              <Mark size={44} />
              <p className="font-display text-base text-ink-900 mt-1">No messages yet</p>
              <p className="text-xs text-ink-400 font-mono">Send a message below to start the conversation.</p>
            </div>
          )}

          {/* Message list */}
          {messages.map((msg) => {
            const showDivider = msg.date && msg.date !== lastDate;
            if (msg.date) lastDate = msg.date;

            return (
              <div key={msg.id}>
                {showDivider && <DateDivider label={msg.date} />}
                <MessageBubble message={msg} />
              </div>
            );
          })}

          {/* Typing indicator while waiting for API response */}
          {isLoading && (
            <div>
              <TypingIndicator />
            </div>
          )}

          {/* Sentinel element for auto-scroll */}
          <div ref={bottomRef} className="h-2" />
        </div>
      </div>

      {/* Scroll-to-bottom button */}
      <ScrollButton onClick={scrollToBottom} visible={showScrollBtn} />
    </div>
  );
}
