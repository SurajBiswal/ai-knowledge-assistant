import { useState, useCallback, useRef } from "react";
import Header from "../components/layout/Header";
import Sidebar from "../components/layout/Sidebar";
import ChatWindow from "../components/chat/ChatWindow";
import ChatInput from "../components/chat/ChatInput";
import {
  createConversation,
  getConversations,
  getMessages,
  renameConversation,
  sendMessage,
  sendMessageStream, // STREAMING: Import the streaming function
} from "../services/conversationService";
import { useEffect } from "react";



let nextId = 1;

/** Inline error banner shown inside the chat stream */
function ErrorBanner({ message, onDismiss }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3 rounded-md bg-clay-tint border border-clay/30 text-sm text-clay-dark shadow-sm">
      <svg
        className="w-4 h-4 flex-shrink-0 mt-0.5 text-clay"
        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
      <span className="flex-1">{message}</span>
      <button
        onClick={onDismiss}
        className="flex-shrink-0 text-clay/70 hover:text-clay transition-colors"
        aria-label="Dismiss error"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

/**
 * ChatPage
 *
 * Owns all conversation state and orchestrates:
 *   Sidebar → Header → ChatWindow → ChatInput → chatService
 */
export default function ChatPage({ user, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false); // true from send until first streamed chunk arrives
  const [error, setError] = useState(null);       // { message: string } | null
  const [sidebarOpen, setSidebarOpen] = useState(false);
  

  // Prevent double-sends if the user submits before the previous resolves
  const pendingRef = useRef(false);

  const appendMessage = useCallback((role, content) => {
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role,
        content,
      },
    ]);
  }, []);

  const handleSend = useCallback(
    async (text) => {
      if (!activeConversationId) {
        return;
      }

      // STREAMING: Add user message to UI immediately
      appendMessage("user", text);

      // STREAMING: Show the typing indicator until the first chunk arrives —
      // the assistant bubble itself is only created once there's content,
      // so no empty bubble flashes before generation starts.
      const assistantMessageId = crypto.randomUUID();
      let bubbleCreated = false;
      setIsGenerating(true);
      setIsLoading(false); // STREAMING: no separate loading spinner - handled via isGenerating

      try {
        // STREAMING: Use streaming endpoint instead of waiting for full response
        await sendMessageStream(
          activeConversationId,
          text,
          (chunk) => {
            if (!bubbleCreated) {
              bubbleCreated = true;
              setIsGenerating(false);
              setMessages((prev) => [
                ...prev,
                {
                  id: assistantMessageId,
                  role: "assistant",
                  content: chunk,
                },
              ]);
            } else {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? {
                        ...msg,
                        content: msg.content + chunk,
                      }
                    : msg
                )
              );
            }
          }
        );

        // Reload messages so the saved assistant message
        // (including sources) replaces the temporary one.
        await selectConversation(activeConversationId);

        // Refresh sidebar (conversation title)
        await loadConversations();
      } catch (err) {
        setError({
          message:
            err?.message ??
            "Failed to send message",
        });
      } finally {
        setIsGenerating(false);
      }
    },
    [activeConversationId, appendMessage]
  );

  const loadConversations = async () => {
    try {
      const data = await getConversations();

      setConversations(data);

      if (activeConversationId) {
          await selectConversation(activeConversationId);
      } else if (data.length > 0) {
          await selectConversation(data[0].id);
      }
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  const selectConversation = async (
    conversationId
  ) => {
    setActiveConversationId(
      conversationId
    );

    const messages =
      await getMessages(conversationId);

    setMessages(
      messages.map((msg) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        sources: msg.sources ?? [],
        time: "",
        date: "",
      }))
    );
  };

  const createNewConversation = async () => {
    try {
      const conversation =
        await createConversation(
          "New Chat"
        );

      setConversations((prev) => [
        conversation,
        ...prev,
      ]);

      await selectConversation(
        conversation.id
      );
    } catch (error) {
      console.error(error);
    }
  };

  const handleRenameConversation = async (conversationId) => {
    const conversation = conversations.find(
      (c) => c.id === conversationId
    );
    const newTitle = window.prompt(
      "Rename conversation:",
      conversation?.title || ""
    );

    if (!newTitle || newTitle.trim() === "")
      return;

    try {
      await renameConversation(
        conversationId,
        newTitle.trim()
      );
      await loadConversations();
    } catch (error) {
      console.error(
        "Failed to rename conversation:",
        error
      );
    }
  };

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  );
  const headerTitle = activeConversation?.title || "New conversation";

  const groundedDocCount = new Set(
    messages.flatMap((m) => (m.sources || []).map((s) => s.filename))
  ).size;
  const headerSubtitle =
    groundedDocCount > 0
      ? `Grounded in ${groundedDocCount} document${groundedDocCount > 1 ? "s" : ""}`
      : "Ask anything — I'll find the best answer";

  return (
    <div className="flex h-screen overflow-hidden bg-paper font-sans">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        conversations={conversations}
        activeConversationId={
          activeConversationId
        }
        onSelectConversation={
          selectConversation
        }
        onNewConversation={
          createNewConversation
        }
        onRenameConversation={
          handleRenameConversation
        }
        user={user}
        onLogout={onLogout}
      />

      {/* Main column */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Header */}
        <Header
          onMenuToggle={() => setSidebarOpen((v) => !v)}
          title={headerTitle}
          subtitle={headerSubtitle}
        />

        {/* Messages — grows to fill available space */}
        <ChatWindow
          messages={messages}
          isLoading={isGenerating}
          className="flex-1 min-h-0"
        />

        {/* Error banner — sits above input, inside the chat column */}
        {error && (
          <div className="max-w-2xl mx-auto w-full px-4 pb-2">
            <ErrorBanner
              message={error.message}
              onDismiss={() => setError(null)}
            />
          </div>
        )}

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          isLoading={isLoading}
          disabled={false}
        />
      </div>
    </div>
  );
}
