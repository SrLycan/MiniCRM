const STORAGE_KEY = "orbita-theme";

function applyTheme(theme, toggle) {
  const isDark = theme === "dark";
  document.documentElement.dataset.theme = theme;
  toggle.querySelector(".nav__label").textContent = isDark ? "Modo claro" : "Modo oscuro";
}

export function initThemeToggle() {
  const toggle = document.querySelector("[data-theme-toggle]");
  applyTheme(document.documentElement.dataset.theme, toggle);

  toggle.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    sessionStorage.setItem(STORAGE_KEY, nextTheme);
    applyTheme(nextTheme, toggle);
  });
}
