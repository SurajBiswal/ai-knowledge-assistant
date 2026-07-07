import { useState } from "react";
import FileUpload from "../upload/FileUpload";
import DocumentList from "../upload/DocumentList";

function NavIcon({ children, label, active = false }) {
  return (
    <button
      title={label}
      className={`flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors duration-150 group
        ${active
          ? "bg-indigo-50 text-indigo-700 font-medium"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        }`}
    >
      <span className="w-5 h-5 flex items-center justify-center flex-shrink-0">
        {children}
      </span>
      <span className="truncate">{label}</span>
    </button>
  );
}

export default function Sidebar({
  isOpen,
  onClose,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  user,
  onLogout,
  onRenameConversation,
}) {

  const [documentsOpen, setDocumentsOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const handleDocumentsRefresh = () => setRefreshKey((k) => k + 1);

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-20 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`
          fixed top-0 left-0 h-full z-30 flex flex-col bg-slate-50 border-r border-slate-200
          transition-transform duration-300 ease-in-out
          lg:static lg:translate-x-0 lg:z-auto
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
        style={{ width: "280px", minWidth: "280px" }}
      >
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-4 py-4 border-b border-slate-200">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900 leading-tight">KnowledgeAI</p>
            <p className="text-xs text-slate-400">Your intelligent assistant</p>
          </div>
        </div>

        {/* New chat button */}
        <div className="px-3 pt-3 pb-2">
          <button
            onClick={onNewConversation}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-sm font-medium transition-colors duration-150 shadow-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New conversation
          </button>
        </div>

        {/* Navigation */}
        <nav className="px-3 pb-2 flex flex-col gap-0.5">
          <NavIcon label="Home" active>
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} className="w-full h-full">
              <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
            </svg>
          </NavIcon>
          <NavIcon label="Knowledge Base">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} className="w-full h-full">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
            </svg>
          </NavIcon>
          <NavIcon label="Saved Answers">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} className="w-full h-full">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
            </svg>
          </NavIcon>
          <NavIcon label="Settings">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} className="w-full h-full">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 010 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 010-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </NavIcon>
        </nav>

        {/* Divider */}
        <div className="mx-3 border-t border-slate-200 my-1" />

        {/* Documents (collapsible) */}
        <div className="px-3 pt-2">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest px-2 mb-2">
            Documents
          </p>

          <button
            onClick={() => setDocumentsOpen((v) => !v)}
            aria-expanded={documentsOpen}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          >
            <span>📄</span>
            <span>Documents</span>
            <span className="ml-auto text-xs text-slate-400">{documentsOpen ? '▾' : '▸'}</span>
          </button>

          {documentsOpen && (
            <div className="mt-3 px-1">
              <div className="rounded-md bg-white p-2">
                <FileUpload onUploadSuccess={handleDocumentsRefresh} />
                <div className="mt-2">
                  <DocumentList refreshTrigger={refreshKey} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="mx-3 border-t border-slate-200 my-2" />

        {/* Recent Chats */}
        <div className="flex-1 overflow-y-auto px-3 pt-2 min-h-0">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest px-2 mb-2">Recent</p>
          <div className="flex flex-col gap-0.5">
            {conversations.length === 0 ? (
              <div className="px-3 py-4 text-sm text-slate-400">
                No conversations yet
              </div>
            ) : (
              conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className="flex items-center gap-1 group"
                >
                  <button
                    onClick={() =>
                      onSelectConversation(
                        conversation.id
                      )
                    }
                    className={`flex-1 text-left px-3 py-2 rounded-lg transition-colors duration-150
        ${activeConversationId ===
                      conversation.id
                      ? "bg-indigo-50 text-indigo-800"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    <p className="text-sm truncate leading-snug">
                      {conversation.title}
                    </p>

                    <p
                      className={`text-[11px] mt-0.5 ${activeConversationId ===
                          conversation.id
                          ? "text-indigo-400"
                          : "text-slate-400"
                        }`}
                    >
                      {new Date(
                        conversation.updated_at
                      ).toLocaleDateString()}
                    </p>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (
                        typeof onRenameConversation ===
                        "function"
                      ) {
                        onRenameConversation(
                          conversation.id
                        );
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-600 px-1 py-2 text-sm transition-opacity"
                    title="Rename"
                  >
                    ✎
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* User profile */}
        <div className="px-3 py-3 border-t border-slate-200">
          <div className="w-full flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-slate-100 transition-colors duration-150">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-bold text-white">{(user && user.name) ? user.name.split(" ").map(n=>n[0]).slice(0,2).join("") : "JD"}</span>
            </div>
            <div className="flex-1 text-left min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">{user?.name ?? "Jane Doe"}</p>
              <p className="text-xs text-slate-400 truncate">{user?.email ?? "Pro plan"}</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => { if (typeof onLogout === 'function') onLogout(); }}
                className="text-xs text-slate-500 hover:text-slate-700"
              >
                Logout
              </button>
              <svg className="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
