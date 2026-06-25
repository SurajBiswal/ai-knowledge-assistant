import { useEffect, useState } from "react";
import ChatPage from "./pages/ChatPage";
import LoginPage from "./pages/LoginPage";
import { getCurrentUser } from "./services/authService";

function getInitialRoute() {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token ? "/chat" : "/login";
}

export default function App() {
  const [route, setRoute] = useState(getInitialRoute);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const onPop = () => setRoute(window.location.pathname || "/");
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    if (window.location.pathname !== route) {
      window.history.replaceState({}, "", route);
    }
  }, [route]);

  useEffect(() => {
    // On startup or when route changes to /chat, if token exists try to load user
    const tryLoadUser = async () => {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      if (!token) {
        setUser(null);
        setRoute("/login");
        return;
      }

      try {
        const u = await getCurrentUser();
        setUser(u);
        setRoute("/chat");
      } catch (err) {
        try { localStorage.removeItem("access_token"); } catch (e) {}
        setUser(null);
        setRoute("/login");
      }
    };

    if (route === "/chat") {
      tryLoadUser();
    }
  }, [route]);

  const handleLoginSuccess = () => {
    setRoute("/chat");
  };

  const handleLogout = () => {
    try { localStorage.removeItem("access_token"); } catch (e) {}
    setUser(null);
    setRoute("/login");
  };

  if (route === "/login") {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return <ChatPage user={user} onLogout={handleLogout} />;
}