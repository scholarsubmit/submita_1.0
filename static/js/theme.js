(function () {
  const STORAGE_KEY = 'submita-theme';

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const toggleIcon = document.querySelector('[data-theme-icon]');
    if (toggleIcon) toggleIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
  }

  function getInitialTheme() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  // Apply immediately (before paint) to avoid a flash of the wrong theme.
  applyTheme(getInitialTheme());

  document.addEventListener('DOMContentLoaded', function () {
    const toggleBtn = document.querySelector('[data-theme-toggle]');
    if (!toggleBtn) return;
    toggleBtn.addEventListener('click', function () {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem(STORAGE_KEY, next);
      applyTheme(next);
    });
  });
})();
