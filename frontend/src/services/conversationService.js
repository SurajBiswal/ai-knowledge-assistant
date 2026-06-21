import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export async function getConversations() {
  const { data } = await api.get("/api/conversations");
  return data;
}

export async function createConversation(title) {
  const { data } = await api.post(
    "/api/conversations",
    {
      title,
      mode: "chat",
    }
  );

  return data;
}

export async function getMessages(
  conversationId
) {
  const { data } = await api.get(
    `/api/conversations/${conversationId}/messages`
  );

  return data;
}

export async function sendMessage(
  conversationId,
  content
) {
  const { data } = await api.post(
    `/api/conversations/${conversationId}/messages`,
    {
      content,
    }
  );

  return data;
}

export async function deleteConversation(
  conversationId
) {
  const { data } = await api.delete(
    `/api/conversations/${conversationId}`
  );

  return data;
}