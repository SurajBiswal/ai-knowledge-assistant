import api from "./api";
const BASE_URL = import.meta.env.VITE_API_BASE_URL;

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

// STREAMING: New function for streaming message responses
// Instead of waiting for full response, this streams chunks as they arrive
export async function sendMessageStream(
  conversationId,
  content,
  onChunk // STREAMING: Callback function that receives each text chunk
) {
  // STREAMING: Use fetch instead of axios for streaming support
  const headers = {
    "Content-Type": "application/json",
  };

  try {
    const token = localStorage.getItem("access_token");
    if (token) headers.Authorization = `Bearer ${token}`;
  } catch (e) {
    // ignore
  }

  const response = await fetch(
    `${BASE_URL}/api/conversations/${conversationId}/messages/stream`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        content,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  // STREAMING: Read the response body as a stream
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      // STREAMING: Decode chunk and pass to callback
      const chunk = decoder.decode(value, { stream: true });
      if (chunk) {
        onChunk(chunk);  // STREAMING: Frontend updates message with this chunk
      }
    }
  } finally {
    reader.cancel();
  }
}

export async function deleteConversation(
  conversationId
) {
  const { data } = await api.delete(
    `/api/conversations/${conversationId}`
  );

  return data;
}