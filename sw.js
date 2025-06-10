// EDS Uyarı Sistemi - Service Worker
// Version 2.0.0

const CACHE_NAME = 'eds-alert-v2.0.0';
const CACHE_URLS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/data/eds-locations.geojson',
    '/css/style.css',
    '/js/utils.js',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Install event - cache resources
self.addEventListener('install', event => {
    console.log('📦 Service Worker installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('📦 Caching app resources');
                return cache.addAll(CACHE_URLS.map(url => {
                    return new Request(url, { mode: 'no-cors' });
                })).catch(error => {
                    console.warn('⚠️ Some resources failed to cache:', error);
                    // Cache individual files that work
                    return Promise.allSettled(
                        CACHE_URLS.map(url => cache.add(url).catch(e => console.warn('Failed to cache:', url)))
                    );
                });
            })
            .then(() => {
                console.log('✅ Service Worker installation complete');
                return self.skipWaiting();
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('🔄 Service Worker activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== CACHE_NAME) {
                            console.log('🗑️ Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('✅ Service Worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // Skip external resources we don't control
    if (!event.request.url.startsWith(self.location.origin) && 
        !event.request.url.includes('unpkg.com') && 
        !event.request.url.includes('cdnjs.cloudflare.com')) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached version if available
                if (response) {
                    console.log('📦 Serving from cache:', event.request.url);
                    return response;
                }

                // Otherwise fetch from network
                console.log('🌐 Fetching from network:', event.request.url);
                return fetch(event.request)
                    .then(response => {
                        // Don't cache if not successful
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        // Clone the response
                        const responseToCache = response.clone();

                        // Add to cache
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });

                        return response;
                    })
                    .catch(error => {
                        console.error('❌ Network fetch failed:', error);
                        
                        // Return offline page for navigation requests
                        if (event.request.mode === 'navigate') {
                            return new Response(`
                                <!DOCTYPE html>
                                <html lang="tr">
                                <head>
                                    <meta charset="UTF-8">
                                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                    <title>🚨 EDS Uyarı Sistemi - Offline</title>
                                    <style>
                                        body {
                                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
                                            color: white;
                                            margin: 0;
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;
                                            min-height: 100vh;
                                            text-align: center;
                                        }
                                        .offline-container {
                                            padding: 2rem;
                                            max-width: 400px;
                                        }
                                        .icon {
                                            font-size: 4rem;
                                            margin-bottom: 1rem;
                                        }
                                        h1 {
                                            margin-bottom: 1rem;
                                            color: #ff4757;
                                        }
                                        p {
                                            margin-bottom: 2rem;
                                            color: #ccc;
                                        }
                                        .retry-btn {
                                            background: #2ed573;
                                            color: white;
                                            border: none;
                                            padding: 12px 24px;
                                            border-radius: 8px;
                                            cursor: pointer;
                                            font-size: 16px;
                                            transition: background 0.3s ease;
                                        }
                                        .retry-btn:hover {
                                            background: #27c668;
                                        }
                                    </style>
                                </head>
                                <body>
                                    <div class="offline-container">
                                        <div class="icon">📡</div>
                                        <h1>Bağlantı Yok</h1>
                                        <p>EDS Uyarı Sistemi şu anda çevrimdışı. İnternet bağlantınızı kontrol edin.</p>
                                        <button class="retry-btn" onclick="window.location.reload()">
                                            🔄 Tekrar Dene
                                        </button>
                                    </div>
                                </body>
                                </html>
                            `, {
                                headers: { 'Content-Type': 'text/html' }
                            });
                        }
                        
                        // For other requests, just reject
                        return Promise.reject(error);
                    });
            })
    );
});

// Background sync for GPS data
self.addEventListener('sync', event => {
    if (event.tag === 'background-gps-sync') {
        console.log('🔄 Background GPS sync triggered');
        event.waitUntil(performBackgroundSync());
    }
});

async function performBackgroundSync() {
    // This would sync GPS data when back online
    try {
        // Implement background sync logic here
        console.log('✅ Background sync completed');
    } catch (error) {
        console.error('❌ Background sync failed:', error);
    }
}

// Push notification handling
self.addEventListener('push', event => {
    if (!event.data) {
        return;
    }

    const data = event.data.json();
    const options = {
        body: data.body || 'Yeni EDS kamerası tespit edildi',
        icon: '/assets/icons/icon-192x192.png',
        badge: '/assets/icons/icon-72x72.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/'
        },
        actions: [
            {
                action: 'open',
                title: 'Aç',
                icon: '/assets/icons/open-icon.png'
            },
            {
                action: 'dismiss',
                title: 'Kapat',
                icon: '/assets/icons/close-icon.png'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'EDS Uyarı', options)
    );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    event.notification.close();

    if (event.action === 'open') {
        event.waitUntil(
            self.clients.openWindow(event.notification.data.url)
        );
    }
});

// Message handling from main app
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// Periodic background sync for EDS data updates
self.addEventListener('periodicsync', event => {
    if (event.tag === 'eds-data-update') {
        console.log('📅 Periodic sync: Updating EDS data');
        event.waitUntil(updateEDSData());
    }
});

async function updateEDSData() {
    try {
        // This would fetch updated EDS data from server
        const response = await fetch('/api/eds-updates');
        if (response.ok) {
            const data = await response.json();
            // Update cached data
            console.log('✅ EDS data updated');
        }
    } catch (error) {
        console.error('❌ EDS data update failed:', error);
    }
}

console.log('📱 EDS Alert Service Worker loaded and ready!');