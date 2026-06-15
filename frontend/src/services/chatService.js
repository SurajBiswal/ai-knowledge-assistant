import axios from "axios";

// const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const BASE_URL = import.meta.env.VITE_API_BASE_URL;

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ── Request interceptor ───────────────────────────────────────────────────────
// Attach auth token if present (e.g. after login is wired up)
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("auth_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor ──────────────────────────────────────────────────────
// Normalise errors into a consistent shape before they reach the UI
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with a non-2xx status
      const { status, data } = error.response;
      const message =
        data?.detail ?? data?.message ?? `Request failed with status ${status}`;
      return Promise.reject({ status, message, raw: error });
    }

    if (error.code === "ECONNABORTED") {
      return Promise.reject({ status: 408, message: "Request timed out. Please try again.", raw: error });
    }

    // Network error / server unreachable
    return Promise.reject({ status: 0, message: "Unable to reach the server. Check your connection.", raw: error });
  }
);

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Send a chat message to the backend.
 *
 * @param {string} message - The user's message text.
 * @returns {Promise<string>} The assistant's response string.
 * @throws {{ status: number, message: string, raw: Error }}
 *
 * @example
 * const reply = await sendMessage("Explain transformers");
 */
export async function sendMessage(message) {
  if (!message || typeof message !== "string" || !message.trim()) {
    throw { status: 400, message: "Message must be a non-empty string.", raw: null };
  }

  const { data } = await apiClient.post("/chat", { message: message.trim() });

  if (typeof data?.response !== "string") {
    throw { status: 502, message: "Unexpected response format from server.", raw: null };
  }

  return data.response;
}

export default { sendMessage };
