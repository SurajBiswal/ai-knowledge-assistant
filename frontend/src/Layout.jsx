import { useState } from "react";

import Sidebar from "./components/layout/Sidebar";
import Header from "./components/layout/Header";
import Mark from "./components/layout/Mark";

const suggestions = [
  { icon: "💡", label: "Explain a concept", sub: "Break down complex ideas simply" },
  { icon: "✍️", label: "Help me write", sub: "Drafts, emails, essays & more" },
  { icon: "🔍", label: "Research a topic", sub: "Summarise and synthesise sources" },
  { icon: "🧮", label: "Solve a problem", sub: "Code, maths, logic & reasoning" },
];

const messages = [
  {
    id: 1,
    role: "user",
    content: "Can you explain how transformer models work in simple terms?",
    time: "2:14 PM",
  },
  {
    id: 2,
    role: "assistant",
    content:
      "Sure! A transformer is a type of neural network architecture that processes sequences — like sentences — by paying attention to all words simultaneously rather than one at a time.\n\nThe key innovation is the **self-attention mechanism**: for each word, the model weighs how relevant every other word is to understanding it. This lets it capture long-range dependencies really well.\n\nHere's the flow in a nutshell:\n1. Input tokens are turned into vectors (embeddings).\n2. Each layer applies self-attention + a small feed-forward network.\n3. Stack enough layers and you get a very rich understanding of the input.",
    time: "2:14 PM",
  },
];

function ChatBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold font-mono
        ${isUser
          ? "bg-moss text-paper-100"
          : "bg-ink text-mustard border border-ink-softer"
        }`}
      >
        {isUser ? "JD" : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        )}
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-line
          ${isUser
            ? "bg-ink text-paper-100 rounded-tr-sm"
            : "bg-surface border border-paper-line text-ink-900 rounded-tl-sm shadow-sm"
          }`}
        >
          {message.content}
        </div>
        <span className="text-[11px] text-ink-400 font-mono px-1">{message.time}</span>
      </div>
    </div>
  );
}

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [showChat, setShowChat] = useState(false);

  function handleSend() {
    if (inputValue.trim()) setShowChat(true);
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-paper font-sans">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} conversations={[]} />

      {/* Main content */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header onMenuToggle={() => setSidebarOpen((v) => !v)} />

        {/* Chat / Welcome area */}
        <main className="flex-1 overflow-y-auto">
          {showChat ? (
            /* Message thread */
            <div className="max-w-2xl mx-auto px-4 py-6 flex flex-col gap-6">
              {messages.map((msg) => (
                <ChatBubble key={msg.id} message={msg} />
              ))}

              {/* Typing indicator */}
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-ink border border-ink-softer flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-mustard" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                </div>
                <div className="bg-surface border border-paper-line rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5 shadow-sm">
                  <span className="w-2 h-2 bg-moss/40 rounded-full animate-bounce [animation-delay:-0.3s]" />
                  <span className="w-2 h-2 bg-moss/70 rounded-full animate-bounce [animation-delay:-0.15s]" />
                  <span className="w-2 h-2 bg-moss rounded-full animate-bounce" />
                </div>
              </div>
            </div>
          ) : (
            /* Welcome / empty state */
            <div className="flex flex-col items-center justify-center h-full px-6 text-center gap-8">
              <div>
                <div className="mb-4 flex justify-center">
                  <Mark size={56} />
                </div>
                <h2 className="font-display text-2xl text-ink-900">What can I help with?</h2>
                <p className="text-ink-400 mt-1.5 text-sm max-w-sm mx-auto">
                  Ask me anything — I can explain concepts, help you write, research topics, or think through problems.
                </p>
              </div>

              {/* Suggestion cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full max-w-2xl">
                {suggestions.map((s) => (
                  <button
                    key={s.label}
                    onClick={() => setInputValue(s.label)}
                    className="flex flex-col items-start gap-2 p-3.5 rounded-lg border border-paper-line hover:border-moss hover:bg-moss-tint/40 text-left transition-colors duration-150 group"
                  >
                    <span className="text-xl">{s.icon}</span>
                    <div>
                      <p className="text-sm font-medium text-ink-900 group-hover:text-moss-dark leading-snug">{s.label}</p>
                      <p className="text-xs text-ink-400 mt-0.5 leading-snug">{s.sub}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </main>

        {/* Input bar */}
        <div className="px-4 pb-4 pt-2 bg-paper border-t border-paper-line">
          <div className="max-w-2xl mx-auto">
            <div className="flex items-end gap-2 bg-surface border border-paper-line rounded-2xl px-4 py-3 focus-within:border-ink-400 transition-colors duration-150 shadow-sm">
              {/* Attachment */}
              <button
                title="Attach file"
                className="p-1 text-ink-400 hover:text-moss transition-colors duration-150 flex-shrink-0 mb-0.5"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
                </svg>
              </button>

              {/* Textarea */}
              <textarea
                rows={1}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask anything…"
                className="flex-1 bg-transparent resize-none outline-none text-sm text-ink-900 placeholder-ink-400 leading-relaxed max-h-32"
              />

              {/* Send */}
              <button
                onClick={handleSend}
                disabled={!inputValue.trim()}
                title="Send message"
                className={`p-1.5 rounded-lg flex-shrink-0 mb-0.5 transition-colors duration-150
                  ${inputValue.trim()
                    ? "bg-mustard hover:bg-mustard-dark text-ink"
                    : "bg-paper-dim text-ink-400 cursor-not-allowed"
                  }`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              </button>
            </div>
            <p className="text-[11px] text-ink-400 font-mono text-center mt-2">
              KnowledgeAI can make mistakes. Verify important information.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
