import { useState } from "react";
import { login as loginService } from "../services/authService";
import Mark from "../components/layout/Mark";

export default function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await loginService(email, password);
      setLoading(false);
      if (typeof onLoginSuccess === "function") onLoginSuccess();
    } catch (err) {
      setLoading(false);
      setError(err?.message ?? "Login failed");
    }
  };

  // TODO(backend): no Google OAuth endpoint yet — wire this up once
  // the backend exposes one (e.g. GET /api/auth/google or similar).
  const handleGoogleLogin = () => {
    console.warn("Google sign-in is not wired to a backend endpoint yet.");
  };

  // TODO(backend): no account-creation / password-reset endpoints yet —
  // wire these up once the backend exposes them.
  const handleForgotPassword = (e) => {
    e.preventDefault();
    console.warn("Forgot-password flow is not wired to a backend endpoint yet.");
  };
  const handleCreateAccount = (e) => {
    e.preventDefault();
    console.warn("Account-creation flow is not wired to a backend endpoint yet.");
  };

  return (
    <div className="min-h-screen flex bg-ink font-sans">
      {/* Left — ink panel, brand */}
      <div className="hidden lg:flex lg:w-[42%] bg-ink text-paper-100 flex-col justify-between p-12 relative overflow-hidden">
        <div className="flex items-center gap-3">
          <Mark size={34} />
          <div>
            <p className="font-display text-lg tracking-wide">KnowledgeAI</p>
            <p className="text-[11px] font-mono uppercase tracking-widest text-paper-400">Your archive, indexed</p>
          </div>
        </div>

        <div className="max-w-sm">
          <p className="font-display text-3xl leading-snug text-paper-100">
            Every answer, <em className="text-mustard not-italic font-medium">traced back</em> to its source.
          </p>
          <p className="mt-4 text-sm text-paper-400 leading-relaxed">
            Upload your documents and ask questions in plain language. KnowledgeAI cites the exact page and passage behind every response.
          </p>

          {/* Citation preview card */}
          <div className="mt-8 rounded-lg border border-ink-softer bg-ink-soft p-4">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-moss flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              <span className="text-sm font-medium text-paper-100">SSO_Onboarding_Guide.docx</span>
            </div>
            <p className="mt-2.5 text-sm text-paper-400 italic leading-relaxed">
              "After successful login, SSO redirects the user back to the configured callback URL…"
            </p>
            <span className="mt-2.5 inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-mono font-semibold text-moss bg-moss-tint/20 border border-moss/30">
              " page 4, paragraph 2
            </span>
          </div>
        </div>

        <p className="text-[11px] font-mono text-paper-400/70">© {new Date().getFullYear()} KnowledgeAI</p>
      </div>

      {/* Right — dark panel, form as a "borrower's card" */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 bg-ink">
        <div className="w-full max-w-sm">
          {/* Mobile brand */}
          <div className="flex lg:hidden items-center gap-2.5 mb-8">
            <Mark size={28} />
            <p className="font-display text-lg text-paper-100">KnowledgeAI</p>
          </div>

          <p className="font-mono text-[11px] uppercase tracking-widest text-moss mb-2">Sign in</p>
          <h1 className="font-display text-2xl text-paper-100 mb-6">Welcome back</h1>

          {error && (
            <div className="mb-5 text-sm text-clay-dark bg-clay-tint border border-clay/30 px-3 py-2 rounded-md">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[11px] font-mono uppercase tracking-widest text-paper-400 mb-1.5">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="block w-full rounded-md border border-ink-softer bg-ink-soft px-3.5 py-2.5 text-sm text-paper-100 placeholder-paper-400/60 shadow-sm outline-none transition-colors focus:border-paper-400"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-[11px] font-mono uppercase tracking-widest text-paper-400">
                  Password
                </label>
                <a
                  href="#"
                  onClick={handleForgotPassword}
                  className="text-[11px] text-paper-400 hover:text-mustard transition-colors"
                >
                  Forgot password?
                </a>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full rounded-md border border-ink-softer bg-ink-soft px-3.5 py-2.5 text-sm text-paper-100 placeholder-paper-400/60 shadow-sm outline-none transition-colors focus:border-paper-400"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex items-center justify-center rounded-md bg-mustard px-4 py-2.5 text-sm font-semibold text-white hover:bg-mustard-dark disabled:opacity-50 transition-colors mt-2"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-ink-softer" />
            <span className="text-[11px] font-mono text-paper-400">or</span>
            <div className="flex-1 h-px bg-ink-softer" />
          </div>

          {/* Google sign-in — UI only for now, see TODO above */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="w-full inline-flex items-center justify-center gap-2.5 rounded-md border border-ink-softer bg-ink-soft px-4 py-2.5 text-sm font-medium text-paper-100 hover:bg-ink-softer transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.47a5.54 5.54 0 01-2.4 3.63v3h3.88c2.27-2.09 3.57-5.17 3.57-8.82z" />
              <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.95-2.91l-3.88-3c-1.08.72-2.45 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.96H1.27v3.11A11.996 11.996 0 0012 24z" />
              <path fill="#FBBC05" d="M5.27 14.28A7.2 7.2 0 014.88 12c0-.79.14-1.56.39-2.28V6.61H1.27A11.996 11.996 0 000 12c0 1.94.46 3.77 1.27 5.39l4-3.11z" />
              <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.44-3.44C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.69 1.27 6.61l4 3.11C6.22 6.86 8.87 4.75 12 4.75z" />
            </svg>
            Continue with Google
          </button>

          <p className="mt-6 text-center text-sm text-paper-400">
            New here?{" "}
            <a
              href="#"
              onClick={handleCreateAccount}
              className="text-moss hover:text-mustard font-medium transition-colors"
            >
              Create an account
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
