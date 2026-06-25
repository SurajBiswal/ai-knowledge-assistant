import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
	baseURL: BASE_URL,
	headers: {
		"Content-Type": "application/json",
	},
});

// Attach Authorization header automatically when access_token is present
api.interceptors.request.use((config) => {
	try {
		const token = localStorage.getItem("access_token");
		if (token) {
			config.headers = config.headers || {};
			config.headers.Authorization = `Bearer ${token}`;
		}
	} catch (e) {
		// ignore localStorage errors (e.g. SSR environments)
	}

	return config;
});

export default api;
