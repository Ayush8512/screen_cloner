// AirScreen Client Service Worker for PWA Standalone Mode
const CACHE_NAME = "airscreen-v3.0";
const ASSETS = [
  "/",
  "/static/css/main.css",
  "/static/js/connection.js",
  "/static/js/renderer.js",
  "/static/js/controls.js",
  "/static/js/app.js",
  "/static/manifest.json",
  "/static/icon.svg"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  // Let WebSocket and live stream bypass cache
  if (e.request.url.includes("/ws") || e.request.url.includes("/api/")) {
    return;
  }
  e.respondWith(
    caches.match(e.request).then((res) => {
      return res || fetch(e.request);
    })
  );
});
