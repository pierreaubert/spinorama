import { urlParameters2Sort } from './search.js';

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

sleep(5000).then(() => {
    const url = new URL(window.location.href);
    const params = urlParameters2Sort(url);
    const keywords = params[2];
    const counter = document.getElementById('speakers').children.length;
    // if no speaker displayed and no keyword
    if (counter === 0 && keywords === '') {
        const alert = document.getElementById('alert');
        alert.classList.remove('hidden');
        const debug = document.getElementById('alertdebug');
        debug.textContent = '';
        const makeItem = (text) => {
            const li = document.createElement('li');
            li.textContent = text;
            return li;
        };
        debug.appendChild(makeItem('Found: ' + counter + ' speakers'));
        debug.appendChild(makeItem(' Href: ' + (window?.location.href ?? '')));
        debug.appendChild(makeItem(' Browser' + (window?.navigator.appVersion ?? '')));
    }
});
