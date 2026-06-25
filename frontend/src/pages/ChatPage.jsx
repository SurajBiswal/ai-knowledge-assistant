import { useState, useCallback, useRef } from "react";
import Header from "../components/layout/Header";
import Sidebar from "../components/layout/Sidebar";
import ChatWindow from "../components/chat/ChatWindow";
import ChatInput from "../components/chat/ChatInput";
import {
  createConversation,
  getConversations,
  getMessages,
  sendMessage,
  sendMessageStream, // STREAMING: Import the streaming function
} from "../services/conversationService";
import { useEffect } from "react";



let nextId = 1;

/** Inline error banner shown inside the chat stream */
function ErrorBanner({ message, onDismiss }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-rose-50 border border-rose-200 text-sm text-rose-700 shadow-sm">
      <svg
        className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-500"
        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
      <span className="flex-1">{message}</span>
      <button
        onClick={onDismiss}
        className="flex-shrink-0 text-rose-400 hover:text-rose-600 transition-colors"
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
export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
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
      const userMessageId = crypto.randomUUID();
      appendMessage("user", text);

      // STREAMING: Create empty assistant message that will be updated with chunks
      const assistantMessageId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMessageId,
          role: "assistant",
          content: "", // STREAMING: Empty initially, will be filled with chunks
        },
      ]);

      setIsLoading(false); // STREAMING: No loading spinner - message updates in real-time

      try {
        // STREAMING: Use streaming endpoint instead of waiting for full response
        await sendMessageStream(
          activeConversationId,
          text,
          // STREAMING: Callback that runs for each chunk received from backend
          (chunk) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? // STREAMING: Append chunk to existing assistant message
                    { ...msg, content: msg.content + chunk }
                  : msg
              )
            );
          }
        );
      } catch (err) {
        setError({
          message:
            err?.message ??
            "Failed to send message",
        });
      }
    },
    [activeConversationId, appendMessage]
  );

  const loadConversations = async () => {
    try {
      const data = await getConversations();

      setConversations(data);

      if (data.length > 0) {
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

  return (
    <div className="flex h-screen overflow-hidden bg-white font-sans">
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
      />

      {/* Main column */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Header */}
        <Header onMenuToggle={() => setSidebarOpen((v) => !v)} />

        {/* Messages — grows to fill available space */}
        <ChatWindow
          messages={messages}
          isTyping={isLoading}
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
