const CACHE = "mitaka-static-v4";
const ASSETS = ["/static/pwa/manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS).catch(() => undefined)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const isNavigate = req.mode === "navigate";
  const isStyleOrScript = url.pathname.startsWith("/static/css/") || url.pathname.startsWith("/static/js/");
  if (isNavigate) {
    event.respondWith(fetch(req, { cache: "no-store" }));
    return;
  }
  if (isStyleOrScript) {
    event.respondWith(fetch(req).catch(() => caches.match(req)));
    return;
  }
  event.respondWith(caches.match(req).then((cached) => cached || fetch(req).catch(() => cached)));
});
