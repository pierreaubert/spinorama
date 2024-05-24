import {Workbox} from "/js3rd/workbox-window-${versions['WORKBOX']}${min}.js";

if ('serviceWorker' in navigator) {
    const wb = new Workbox('/sw.js');

    wb.addEventListener('install', () => {
	self.skipWaiting();
    });

    wb.addEventListener('activate', (event) => {
	self.clients.matchAll({
	    type: 'window'
	}).then(windowClients => {
	    windowClients.forEach((windowClient) => {
		windowClient.navigate(windowClient.url);
	    });
	});
	if (!event.isUpdate) {
            console.log('Service worker activated for the first time!');
	}
    });

    wb.addEventListener('waiting', event => {
	console.log(
	    `A new service worker has installed, but it can't activate` +
		`until all tabs running the current version have fully unloaded.`);
    });
    
    wb.addEventListener('message', event => {
	if (event.data.type === 'CACHE_UPDATED') {
	    const {updatedURL} = event.data.payload;
	    console.log('A newer version of '+updatedURL+' is available!');
	}
    });
    
    wb.register();
}

