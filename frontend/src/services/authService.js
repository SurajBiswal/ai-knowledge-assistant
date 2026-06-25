import api from "./api";

export async function login(email, password) {
  try {
    const { data } = await api.post("/api/auth/login", {
      email,
      password,
    });

    if (data && data.access_token) {
      localStorage.setItem("access_token", data.access_token);
    }

    return data;
  } catch (err) {
    // Normalize error for callers
    if (err.response && err.response.data && err.response.data.detail) {
      throw new Error(err.response.data.detail);
    }

    throw err;
  }
}

export async function getCurrentUser() {
  try {
    const { data } = await api.get("/api/auth/me");
    return data;
  } catch (err) {
    // If unauthorized or token expired, remove stored token
    if (err.response && (err.response.status === 401 || err.response.status === 403)) {
      try {
        localStorage.removeItem("access_token");
      } catch (e) {
        // ignore
      }
    }

    throw err;
  }
}

export default {
  login,
  getCurrentUser,
};
