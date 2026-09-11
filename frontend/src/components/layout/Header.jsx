import ThemeToggle from "./ThemeToggle";

export default function Header({
  onMenuToggle,
  title = "New conversation",
  subtitle = "Ask anything — I'll find the best answer",
}) {
  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-paper-line bg-paper/90 backdrop-blur-sm flex-shrink-0 z-10">
      {/* Left — mobile menu + title */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Hamburger — visible only on mobile */}
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-1.5 rounded-md text-ink-600 hover:bg-paper-dim transition-colors duration-150 flex-shrink-0"
          aria-label="Open sidebar"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>

        <div className="min-w-0">
          <h1 className="font-display text-[15px] text-ink-900 leading-tight truncate">{title}</h1>
          <p className="text-xs text-ink-400 hidden sm:block font-mono truncate">{subtitle}</p>
        </div>
      </div>

      {/* Right — controls */}
      <div className="flex items-center gap-1.5">
        {/* Theme toggle */}
        <ThemeToggle />

        {/* Share */}
        <button
          title="Share conversation"
          className="p-2 rounded-md text-ink-600 hover:bg-paper-dim hover:text-ink-900 transition-colors duration-150"
        >
          <svg className="w-4.5 h-4.5 w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
          </svg>
        </button>

        {/* More options */}
        <button
          title="More options"
          className="p-2 rounded-md text-ink-600 hover:bg-paper-dim hover:text-ink-900 transition-colors duration-150"
        >
          <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
          </svg>
        </button>
      </div>
    </header>
  );
}
