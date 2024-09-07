//

import { registerRoute, Route } from 'workbox-routing';
import { CacheFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';

const imagesRoute = new Route(
    ({ request, sameOrigin }) => {
        return sameOrigin && request.destination === 'image';
    },
    new CacheFirst({
        cacheName: 'images',
        plugins: [
            new ExpirationPlugin({
                maxEntries: 2500,
                maxAgeSeconds: 60 * 60 * 24,
            }),
        ],
    })
);

const scriptsRoute = new Route(
    ({ request }) => {
        return request.destination === 'script';
    },
    new CacheFirst({
        cacheName: 'scripts',
        plugins: [
            new ExpirationPlugin({
                maxAgeSeconds: 60 * 60 * 2,
            }),
        ],
    })
);

const stylesRoute = new Route(
    ({ request }) => {
        return request.destination === 'style';
    },
    new CacheFirst({
        cacheName: 'styles',
        plugins: [
            new ExpirationPlugin({
                maxAgeSeconds: 60 * 60 * 24 * 10,
            }),
        ],
    })
);

const jsonRoute = new Route(
    ({ request }) => {
        return request.destination === 'json';
    },
    new StaleWhileRevalidate({
        cacheName: 'metadata',
        plugins: [
            new ExpirationPlugin({
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24,
            }),
        ],
    })
);

// Register the new route
registerRoute(imagesRoute);
registerRoute(scriptsRoute);
registerRoute(stylesRoute);
registerRoute(jsonRoute);
