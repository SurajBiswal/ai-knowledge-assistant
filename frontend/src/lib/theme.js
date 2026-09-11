const STORAGE_KEY = "theme";

/** 'light' | 'dark' — resolves saved preference, else system preference. */
export function getInitialTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch (_) {}

  if (typeof window !== "undefined" && window.matchMedia) {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return "light";
}

/** Applies the theme class to <html> so CSS variables in index.css take effect. */
export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
}

export function persistTheme(theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch (_) {}
}
