// Submita service worker — caches static shell assets so the UI (styles,
// scripts, offline page) still renders without a network connection.
// Dynamic data (assignments, grades) always requires a live connection —
// this only keeps the app from looking "broken" when offline.

const CACHE_NAME = 'submita-shell-v1';
const SHELL_ASSETS = [
  '/static/css/main.css',
  '/static/js/theme.js',
  '/static/js/pwa.js',
  '/offline',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  // Static assets: cache-first (fast, works offline).
  if (request.url.includes('/static/')) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
    return;
  }

  // Page navigations: network-first, fall back to a cached offline page.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/offline'))
    );
  }
});
