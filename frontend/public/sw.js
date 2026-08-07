/*
  حوالات — Service Worker (المرحلة 10)
  =======================================
  - قشرة أوفلاين: الصفحات الأساسية والأصول الساكنة تُخزَّن.
  - /api/ و /ws لا تُلمس أبداً (بيانات مالية حيّة — لا تخزين).
  - استراتيجية: أصول Next الساكنة cache-first؛ التنقّل network-first مع
    الرجوع للنسخة المخزنة ثم قشرة الجذر عند الانقطاع.
*/

const CACHE = "hawalat-shell-v1";
const SHELL = ["/", "/login", "/manifest.json", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws/")) return;

  // أصول Next الساكنة: cache-first (أسماؤها مبصومة)
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((res) => {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(request, copy));
            return res;
          })
      )
    );
    return;
  }

  // التنقّل: network-first ثم المخزّن ثم قشرة الجذر
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(request, copy));
          return res;
        })
        .catch(() =>
          caches.match(request).then((hit) => hit || caches.match("/"))
        )
    );
  }
});
