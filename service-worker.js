"use strict";

const CACHE_NAME = "validacion-fall26-v7";
const CORE_ASSETS = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./manifest.webmanifest",
  "./config/settings.json",
  "./data/fall26_checklist.json",
  "./data/export_experience.json",
  "./assets/icons/icon.svg",
  "./assets/icons/apple-touch-icon.png",
  "./assets/icons/icon-192.png",
  "./assets/icons/icon-512.png",
  "./assets/ui/fall26-campaign-reference.webp",
  "./assets/ui/export-working.webp",
  "./assets/ui/export-complete.webp",
  ...[
    "q01", "q02", "q03", "q04", "q05", "q06", "q07", "q09", "q10", "q11", "q12", "q13",
    "q14", "q15", "q16", "q17", "q18", "q19", "q21", "q22", "q23", "q24", "q25", "q26",
    "q27", "q28", "q29", "q30", "q31", "q32", "q33", "q34", "q35", "q36",
  ].map((id) => `./assets/reference/${id}.webp`),
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => caches.match(event.request).then((cached) => cached || caches.match("./index.html"))),
  );
});
