import api from "./api";

function apiErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(" ") || fallback;
  }

  if (typeof detail === "string") {
    return detail;
  }

  return error?.message || fallback;
}

async function request(action, fallback) {
  try {
    const response = await action();
    return response.data;
  } catch (error) {
    throw new Error(apiErrorMessage(error, fallback), { cause: error });
  }
}

const llmProviderService = {
  listProviders() {
    return request(
      () => api.get("/api/ai/providers"),
      "Unable to load available LLM providers."
    );
  },

  listProfiles() {
    return request(
      () => api.get("/api/ai/provider-profiles"),
      "Unable to load LLM provider profiles."
    );
  },

  createProfile(payload) {
    return request(
      () => api.post("/api/ai/provider-profiles", payload),
      "Unable to save the LLM provider profile."
    );
  },

  updateProfile(profileId, payload) {
    return request(
      () => api.put(`/api/ai/provider-profiles/${profileId}`, payload),
      "Unable to update the LLM provider profile."
    );
  },

  deleteProfile(profileId) {
    return request(
      () => api.delete(`/api/ai/provider-profiles/${profileId}`),
      "Unable to delete the LLM provider profile."
    );
  },

  testProfile(profileId) {
    return request(
      () => api.post(`/api/ai/provider-profiles/${profileId}/test`),
      "Unable to test the LLM provider connection."
    );
  },

  activateProfile(profileId) {
    return request(
      () => api.post(`/api/ai/provider-profiles/${profileId}/activate`),
      "Unable to activate the LLM provider profile."
    );
  },
};

export default llmProviderService;
