// Offline support: network-first for same-origin requests, cache-first for the pinned Pico stylesheet.
// Bump CACHE_NAME whenever PRECACHE changes so old entries are evicted.

const CACHE_NAME = "pwa-gripe-v2";
const PRECACHE = [
  "/",
  "/app.js",
  "/manifest.json",
  "https://cdn.jsdelivr.net/npm/@picocss/pico@2.1.1/css/pico.min.css",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(Promise.all([
    self.registration.navigationPreload?.enable(),
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))),
    self.clients.claim(),
  ]));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || !req.url.startsWith("http")) return;
  e.respondWith(new URL(req.url).origin === location.origin ? networkFirst(e) : cacheFirst(e));
});

/** Navigations are keyed without their query string so "/?utm_source=x" still finds "/" offline. */
function cacheKey(req) {
  if (req.mode !== "navigate") return req;
  const url = new URL(req.url);
  url.search = "";
  return url.href;
}

async function networkFirst(e) {
  const key = cacheKey(e.request);
  try {
    const res = (await e.preloadResponse) ?? (await fetch(e.request));
    if (res.ok) e.waitUntil(put(key, res.clone()));
    return res;
  } catch {
    return (await caches.match(key)) ?? Response.error();
  }
}

async function cacheFirst(e) {
  const cached = await caches.match(e.request);
  if (cached) return cached;
  const res = await fetch(e.request);
  if (res.ok) e.waitUntil(put(e.request, res.clone()));
  return res;
}

async function put(key, res) {
  const cache = await caches.open(CACHE_NAME);
  await cache.put(key, res);
}
