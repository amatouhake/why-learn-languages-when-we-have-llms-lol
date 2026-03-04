const CACHE_VERSION = "v10";
const CACHE_NAME = `hsk-${CACHE_VERSION}`;

const PRECACHE_URLS = [
    "/",
    "/style.css?v=8",
    "/app.js?v=8",
    "/manifest.json",
    "/icon-192.png",
    "/icon-512.png",
];

self.addEventListener("install", (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (e) => {
    e.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (e) => {
    const url = new URL(e.request.url);

    // Network-only for API calls
    if (url.pathname.startsWith("/api/")) return;

    // Audio: cache-first, lazy (cache on first play)
    if (url.pathname.startsWith("/audio/")) {
        e.respondWith(
            caches.open(CACHE_NAME).then((cache) =>
                cache.match(e.request).then((cached) => {
                    if (cached) return cached;
                    return fetch(e.request).then((res) => {
                        if (res.ok) cache.put(e.request, res.clone());
                        return res;
                    });
                })
            )
        );
        return;
    }

    // Static assets: cache-first
    e.respondWith(
        caches.match(e.request).then((cached) => cached || fetch(e.request))
    );
});
