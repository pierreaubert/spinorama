// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-2024 Pierre Aubert pierreaubert(at)yahoo(dot)fr
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

import { urlSite, metadataFilenameHead, metadataFilenameChunks, eqdataFilename } from './meta.js';
import { getID } from './misc.js';

function processOrigin(origin) {
    if (origin.includes('Vendors-')) {
        return origin.slice(8);
    }
    return origin;
}

function processGraph(name) {
    if (name.includes('CEA2034')) {
        return 'CEA2034';
    } else if (name.includes('Globe')) {
        return name.replace('Globe', 'Contour');
    }
    return name;
}

function getOrigin(metaSpeakers, speaker, origin) {
    // console.log('getOrigin ' + speaker + ' origin=' + origin)
    const measurements = Object.keys(metaSpeakers[speaker].measurements);
    const origins = new Set();
    for (const key in measurements) {
        origins.add(metaSpeakers[speaker].measurements[measurements[key]].origin);
    }
    if (origin == null || origin === '' || !origins.has(origin)) {
        const defaultMeasurement = metaSpeakers[speaker].default_measurement;
        const defaultOrigin = metaSpeakers[speaker].measurements[defaultMeasurement].origin;
        // console.log('getOrigin default=' + defaultOrigin)
        return processOrigin(defaultOrigin);
    }
    return processOrigin(origin);
}

function getVersion(metaSpeakers, speaker, origin, version) {
    const versions = Object.keys(metaSpeakers[speaker].measurements);
    let matches = new Set();
    versions.forEach((val) => {
        const current = metaSpeakers[speaker].measurements[val];
        if (current.origin === origin || origin === '' || origin == null) {
            matches.add(val);
            matches.add(val + '_eq');
        }
    });
    if (version == null || version === '' || !matches.has(version)) {
        const defaultVersion = metaSpeakers[speaker].default_measurement;
        return defaultVersion;
    }
    return version;
}

function getSpeakerUrl(metaSpeakers, graph, speaker, origin, version) {
    // console.log('getSpeakerUrl ' + graph + ' speaker=' + speaker + ' origin=' + origin + ' version=' + version)
    const url =
        urlSite +
        'speakers/' +
        speaker +
        '/' +
        getOrigin(metaSpeakers, speaker, origin) +
        '/' +
        getVersion(metaSpeakers, speaker, origin, version) +
        '/' +
        processGraph(graph) +
        '.json';
    return url;
}

export function getSpeakerData(metaSpeakers, graph, speaker, origin, version) {
    // console.log('getSpeakerData ' + graph + ' speaker=' + speaker + ' origin=' + origin + ' version=' + version)

    const url = getSpeakerUrl(metaSpeakers, graph, speaker, origin, version);
    // console.log('fetching url=' + url)
    const spec = fetch(url, { headers: { 'Accept-Encoding': 'bz2, gzip, deflate', 'Content-Type': 'application/json' } })
        .then((response) => response.json())
        .catch((error) => {
            console.log('ERROR getSpeaker failed for ' + url + 'with error: ' + error);
            return null;
        });
    return spec;
}

function cleanupCache(url) {
    caches.open('https://dev.spinorama.org').then((cache) => {
        cache.delete(url).then(() => console.info('deleted ' + url + ' from cache.'));
    });
}

function updateCache(url) {
    const urlMeta = '/js/meta-v3.min.js';
    cleanupCache(urlMeta);
    const request = new Request(urlMeta, { cache: 'reload' });
    const spec = fetch(request).then((response) => {
        console.log('cache uploaded: ' + response.text());
        // metadataFilenameHead = response.metadataFilenameHead;
    });
    return spec;
}

export function getAllSpeakers(table) {
    const metaSpeakers = {};
    const speakers = [];
    table.forEach((value) => {
        const speaker = value.brand + ' ' + value.model;
        speakers.push(speaker);
        metaSpeakers[speaker] = value;
    });
    return [metaSpeakers, speakers.sort()];
}

function fetchDataAndMap(url, encoding, state) {
    // console.log('fetching url=' + url + ' encoding=' + encoding);
    const spec = fetch(url, { headers: { 'Accept-Encoding': encoding, 'Content-Type': 'application/json' } })
        .catch((error) => {
            console.log('ERROR fetchData for ' + url + ' ' + error);
            return null;
        })
        .then((response) => {
            if (response.ok) {
                return response.json();
            }
            if (state === 1 && response.status === 404) {
                const newUrl = updateCache(url);
                return fetchDataAndMap(newUrl, encoding, 2);
            }
            console.log('ERROR fetchData for ' + url + ' failed: ' + response.status);
            return null;
        })
        .catch((error) => {
            console.log('ERROR fetchData for ' + url + ' yield a json error: ' + error);
            return null;
        })
        .then((data) => new Map(Object.values(data).map((speaker) => [getID(speaker.brand, speaker.model), speaker])));
    return spec;
}

export function getMetadataHead() {
    const url = urlSite + metadataFilenameHead;
    return fetchDataAndMap(url, 'bz2, zip, deflate', 1);
}

export function getMetadataTail(metadataHead) {
    const promisedChunks = [];
    for (let i in metadataFilenameChunks) {
        const url = urlSite + metadataFilenameChunks[i];
        promisedChunks.push(fetchDataAndMap(url, 1));
    }
    return Promise.all(promisedChunks).then((chunks) => {
        const merged = new Map(metadataHead);
        for (const chunk of chunks) {
            for (const [key, value] of chunk) {
                merged.set(key, value);
            }
        }
        return merged;
    });
}

export function getMetadata() {
    return getMetadataHead().then((data) => getMetadataTail(data));
}

export function getEQdata() {
    const metaDataPromise = getMetadata();
    const url = urlSite + eqdataFilename;
    const eqDataPromise = fetchDataAndMap(url, 'bz2, gzip, zip, deflate', 1).catch((error) => {
        console.log('ERROR getEQdata for ' + url + 'yield a 404 with error: ' + error);
        return null;
    });

    return Promise.all([metaDataPromise, eqDataPromise]).then(([metaData, eqData]) => {
        const mergedData = new Map();
        metaData.forEach((speaker, key) => {
            if (eqData.has(key)) {
                const eqs = eqData.get(key);
                if (eqs.eqs) {
                    speaker['eqs'] = eqs.eqs;
                }
            }
            mergedData.set(key, speaker);
        });
        return mergedData;
    });
}

export function assignOptions(textArray, selector, textSelected) {
    // console.log('assignOptions: selected = ' + textSelected)
    // textArray.forEach( item => // console.log('assignOptions: '+item));
    while (selector.firstChild) {
        selector.firstChild.remove();
    }
    for (const element of textArray) {
        const currentOption = document.createElement('option');
        currentOption.value = element;
        currentOption.text = element.replace('Vendors-', '').replace('vendor-pattern-', 'Pattern ');
        if (element === textSelected) {
            currentOption.selected = true;
        }
        if (textArray.length === 1) {
            currentOption.disabled = true;
        }
        selector.appendChild(currentOption);
    }
}
