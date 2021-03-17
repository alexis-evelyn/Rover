// Import Main Script To Avoid Duplicating Functions and Variables
importScripts("/scripts/main.js")

// Push And Notifications - https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Re-engageable_Notifications_Push
const filesToCache = [
    '/manifest.webmanifest',
    '/scripts/main.js',
    '/scripts/helper.js',
    '/scripts/ethers.js',
    '/css/stylesheet.css',
    '/images/rover.png',
    '/images/rover.svg',
    '/offline',
    '/404',
    '/',
    '/?pwa=true',
    'https://code.jquery.com/jquery-3.5.1.min.js',
    'https://unpkg.com/material-components-web@8.0.0/dist/material-components-web.min.css',
    'https://unpkg.com/material-components-web@8.0.0/dist/material-components-web.min.js',
    'https://fonts.googleapis.com/icon?family=Material+Icons'
];

// Install Pages To Cache
self.addEventListener('install', event => {
    console.debug('Attempting To Install Service Worker And Cache Static Assets!!!');
    event.waitUntil(
        caches.open(staticCacheName)
        .then(cache => {
            return cache.addAll(filesToCache);
        })
    );
});

// Fetch Cached Pages When Offline
self.addEventListener('fetch', event => {
    console.debug('Fetch Event For ', event.request.url);
    event.respondWith(
        caches.match(event.request)
        .then(cache_response => {
            // Load Page From Cache If Cached
            if (cache_response) {
                console.debug('Found, ', event.request.url, ', In Cache');
                return cache_response;
            }

            console.debug("Could Not Find, ", event.request.url, ', In Cache')

            // TODO: DEBUG - Attempt Preload Request
            // if (self.registration.navigationPreload) {
            //     console.debug('Preload Request For ', event.request.url);
            //     return event.preloadResponse.then(preload_response => {
            //         return preload_response;
            //     });
            // }

            // Attempt To Retrieve Page Via Network
            console.debug('Network Request For ', event.request.url);
            return fetch(event.request).then(fetch_response => {
                return caches.open(staticCacheName).then(() => {
                    // Return Fresh Page (200 Status Code)

                    if (fetch_response) {
                        return fetch_response;
                    }
                    console.error("Could Not Fetch, ", event.request.url, '!!!')
                }).catch(() => {
                    // Return Cached 404 Page When Receiving 404 Status Code (And Associate URL With 404 Page)
                    if (fetch_response.status === 404) {
                        caches.put('/404', fetch_response.clone());
                        return fetch_response;
                    }
                });
            });
        }).catch(() => {
            // TODO: Figure Out Why Not Load Cache With If Statement and Remove Hardcoded /?pwa=true
            // if (location.pathname === '/') {
            //     // Return Cached Root Page
            //     return caches.match("/").then(cache => {
            //         console.error("TEST: ", location.pathname)
            //         return cache
            //     });
            // }

            // Return Cached Offline Page
            return caches.match("/offline").then(cache => {
                const init = {"status": 503, "statusText": "Offline"};  // 503 Means Service Unavailable
                return new Response(cache.body, init);
            });
        })
    );
});

// Activate New Service Worker To Replace Caches (Replace staticCacheName to upgrade service worker cache)
self.addEventListener('activate', event => {
    console.debug('Activating New Service Worker!!!');

    const cacheAllowList = [staticCacheName];

    // Activate Navigation Preload Support
    event.waitUntil(async function() {
        if (self.registration.navigationPreload) {
            // Enable navigation preloads!
            console.debug("Navigation Preload Supported!!!")
            // TODO: DEBUG - Enable To Make Browser Preload
            // await self.registration.navigationPreload.enable();
        }
    }());

    // Replace Caches
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheAllowList.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Must Be All Lowercase For Reasons...
self.addEventListener('periodicsync', (event) => {
    if (event.tag === tweetSyncName) {
        // TODO: Check If Needing To Sync

        console.debug("Periodic Sync Triggered For: ", tweetSyncName)
        event.waitUntil(downloadNewTweets());
    }
});