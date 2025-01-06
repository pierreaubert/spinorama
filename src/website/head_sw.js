import { Workbox } from "/js3rd/workbox-window-${versions['WORKBOX']}${min}.js";

function matchOldJS(names) {
    if (names.length > 0) {
        const name = names[0];
        const js = name.match(/\/js\/[a-z]*.min.js/);
        const v5 = name.match(/-v5-/);
        // js file and v5 not in the name
        if (js.length === 1 && v5.length !== 1) {
            return true;
        }
    }
    return false;
}

function cleanupCache() {
    caches.keys().then((name) => {
        // not correct
        if (matchOldJS(name)) {
            console.debug('cleanup caches for entry: ' + name);
            return caches.delete(name);
        }
    });
}

if ('serviceWorker' in navigator) {
    const wb = new Workbox('/sw.js');

    wb.addEventListener('install', (event) => {
        console.log('sw install');
        const promise = self.skipWaiting();
        cleanupCache();
    });

    wb.addEventListener('activate', (event) => {
        console.log('sw activate');
        self.clients
            .matchAll({
                type: 'window',
            })
            .then((windowClients) => {
                windowClients.forEach((windowClient) => {
                    windowClient.navigate(windowClient.url);
                });
            });
        if (!event.isUpdate) {
            console.log('Service worker activated for the first time!');
        } else {
        }
    });

    wb.addEventListener('waiting', () => {
        console.log(
            `A new service worker has installed, but it can't activate` +
                `until all tabs running the current version have fully unloaded.`
        );
    });

    wb.addEventListener('message', (event) => {
        console.log('sw message');
        if (event.data.type === 'CACHE_UPDATED') {
            const { updatedURL } = event.data.payload;
            console.log('A newer version of ' + updatedURL + ' is available!');
        }
    });

    wb.register();
}
