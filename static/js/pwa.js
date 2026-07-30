(function () {
  // Register the service worker for offline shell support.
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js').catch(function (err) {
        console.warn('Service worker registration failed:', err);
      });
    });
  }

  // Capture the install prompt so we can trigger it from our own button
  // instead of relying on the browser's default (often-missed) UI.
  let deferredPrompt = null;

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    const installBtn = document.querySelector('[data-install-app]');
    if (installBtn) installBtn.hidden = false;
  });

  document.addEventListener('DOMContentLoaded', function () {
    const installBtn = document.querySelector('[data-install-app]');
    if (!installBtn) return;
    installBtn.addEventListener('click', async function () {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      deferredPrompt = null;
      installBtn.hidden = true;
    });
  });

  window.addEventListener('appinstalled', function () {
    const installBtn = document.querySelector('[data-install-app]');
    if (installBtn) installBtn.hidden = true;
  });
})();
