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

/*eslint no-undef: "error"*/

import Fuse from 'fuse.js';
import { show } from './misc.js';

const parametersMapping = [
    // filters
    { selectorName: '#selectReviewer', urlParameter: 'reviewer', eventType: 'change' },
    { selectorName: '#selectQuality', urlParameter: 'quality', eventType: 'change' },
    { selectorName: '#selectShape', urlParameter: 'shape', eventType: 'change' },
    { selectorName: '#selectPower', urlParameter: 'power', eventType: 'change' },
    { selectorName: '#selectBrand', urlParameter: 'brand', eventType: 'change' },
    { selectorName: '#inputPriceMin', urlParameter: 'priceMin', eventType: 'change' },
    { selectorName: '#inputPriceMax', urlParameter: 'priceMax', eventType: 'change' },
    { selectorName: '#inputWeightMin', urlParameter: 'weightMin', eventType: 'change' },
    { selectorName: '#inputWeightMax', urlParameter: 'weightMax', eventType: 'change' },
    { selectorName: '#inputHeightMin', urlParameter: 'heightMin', eventType: 'change' },
    { selectorName: '#inputHeightMax', urlParameter: 'heightMax', eventType: 'change' },
    { selectorName: '#inputWidthMin', urlParameter: 'widthMin', eventType: 'change' },
    { selectorName: '#inputWidthMax', urlParameter: 'widthMax', eventType: 'change' },
    { selectorName: '#inputDepthMin', urlParameter: 'depthMin', eventType: 'change' },
    { selectorName: '#inputDepthMax', urlParameter: 'depthMax', eventType: 'change' },
    // search
    { selectorName: '#searchInput', urlParameter: 'search', eventType: 'keyup' },
    // sort
    { selectorName: '#sortBy', urlParameter: 'sort', eventType: 'change' },
    { selectorName: '#sortReverse', urlParameter: 'reverse', eventType: 'change' },
];

const urlToSelectorName = new Map(parametersMapping.map((v) => [v['urlParameter'], v['selectorName']]));

const knownSorter = new Set([
    'brand',
    'date',
    'depth',
    'f3',
    'f6',
    'flatness',
    'height',
    'price',
    'score',
    'scoreEQ',
    'scoreEQWSUB',
    'scoreWSUB',
    'sensitivity',
    'weight',
    'width',
]);

// function printParams(params) {
//     const [sorter, filter, keywords, pagination] = [...params];
//     console.log('  sorter: '+sorter.by+' reverse: '+sorter.reverse);
//     console.log('  filter:'+
// 		' brand='+filter.brand+
// 		' power='+filter.power+
// 		' quality='+filter.quality+
// 		' '+ filter.priceMin+' <=price<= '+ filter.priceMax+
// 		' reviewer='+filter.reviewer+
// 		' shape='+filter.shape);
//     console.log(' keywords='+keywords.toString());
//     console.log(' pagination: page='+pagination.page);
// }

function sortParameters2Sort(url) {
    const sorter = {
        by: 'date',
        reverse: false,
    };
    if (url.searchParams.has('sort')) {
        const sortParams = url.searchParams.get('sort');
        if (knownSorter.has(sortParams)) {
            sorter.by = sortParams;
            const selectorName = urlToSelectorName.get('sort');
            let selector = document.querySelector(selectorName);
            if (selector) {
                selector.value = sortParams;
            } else {
                console.log('Error: selector ' + selectorName + ' is unknown!');
            }
        } else {
            console.log('Error: sort function ' + sortParams + ' is unknown!');
        }
    }

    if (url.searchParams.has('reverse')) {
        const sortOrder = url.searchParams.get('reverse');
        if (sortOrder === 'true') {
            sorter.reverse = true;
        } else {
            sorter.reverse = false;
        }
    } else {
        sorter.reverse = false;
    }
    const selectorName = urlToSelectorName.get('reverse');
    let selector = document.querySelector(selectorName);
    if (selector) {
        selector.value = sorter.reverse;
    } else {
        console.log('Error: selector ' + selectorName + ' is unknown!');
    }

    return sorter;
}

function filtersParameters2Sort(url) {
    const filters = {
        brand: '',
        power: '',
        quality: '',
        priceMin: '',
        priceMax: '',
        weightMin: '',
        weightMax: '',
        widthMin: '',
        widthMax: '',
        depthMin: '',
        depthMax: '',
        heightMin: '',
        heightMax: '',
        reviewer: '',
        shape: '',
    };
    for (const filterName of Object.keys(filters)) {
        if (url.searchParams.has(filterName)) {
            filters[filterName] = url.searchParams.get(filterName);
            const selectorName = urlToSelectorName.get(filterName);
            let selector = document.querySelector(selectorName);
            if (selector) {
                selector.value = filters[filterName];
            } else {
                console.log('Error: filter selector ' + filterName + ' is unknown!');
            }
        }
    }
    return filters;
}

function keywordsParameters2Sort(url) {
    let keywords = '';
    if (url.searchParams.has('search')) {
        keywords = url.searchParams.get('search');
        const selectorName = urlToSelectorName.get('search');
        let selector = document.querySelector(selectorName);
        if (selector) {
            selector.value = keywords.toString();
        } else {
            console.log('Error: search selector ' + selectorName + ' is unknown!');
        }
    }
    return keywords;
}

function paginationParameters2Sort(url) {
    const pagination = {
        page: 1,
        count: 20,
        active: true,
    };

    if (url.searchParams.has('page')) {
        const page = parseInt(url.searchParams.get('page'));
        if (!isNaN(page) || page < 0) {
            pagination.page = page;
            pagination.active = true;
        } else {
            console.log('Warning: ignored parameter page that must be a positive integer (got ' + page + '!');
        }
    }
    if (url.searchParams.has('count')) {
        const count = parseInt(url.searchParams.get('count'));
        if (!isNaN(count) || count < 2) {
            pagination.count = count;
            pagination.active = true;
        } else {
            console.log('Warning: ignored parameter count that must be an integer greater than 1 (got ' + count + '!');
        }
    }
    return pagination;
}

export function urlParameters2Sort(url) {
    const sorter = sortParameters2Sort(url);
    const filters = filtersParameters2Sort(url);
    const keywords = keywordsParameters2Sort(url);
    const pagination = paginationParameters2Sort(url);
    return [sorter, filters, keywords, pagination];
}

export function sortMetadata2(metadata, sorter, results) {
    const sortChildren2 = ({ container, score, reverse }) => {
        // console.log('sorting2 by '+score)
        const items = [...container.keys()];
        if (reverse) {
            items.sort((a, b) => {
                // console.log(score(a), score(b))
                return score(a) - score(b);
            });
        } else {
            items.sort((a, b) => {
                // console.log(score(a), score(b))
                return score(b) - score(a);
            });
        }
        // console.table(items)
        return items;
    };

    function getDateV2(key) {
        const spk = metadata.get(key);
        let date = 19700101;
        // comparing ints (works because 20210101 is bigger than 20201010)
        for (const reviewer in spk.measurements) {
            const msr = spk.measurements[reviewer];
            if (msr && 'review_published' in msr) {
                const reviewPublished = parseInt(msr.review_published);
                if (!isNaN(reviewPublished)) {
                    date = Math.max(reviewPublished, date);
                }
            }
        }
        return date;
    }

    function getPriceV2(key) {
        const spk = metadata.get(key);
        let price = parseFloat(spk.price);
        if (!isNaN(price)) {
            const amount = spk.amount;
            if (amount && amount !== 'each') {
                price /= 2;
                // console.log('getPrice2 each '+price)
            }
            // console.log('getPriceV2 '+price)
            return price;
        }
        // console.log('getPriceV2 noprice')
        return -1;
    }

    function getScoreV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('pref_rating' in msr && 'pref_score' in msr.pref_rating) {
            return spk.measurements[def].pref_rating.pref_score;
        }
        return -10.0;
    }

    function getScoreWsubV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('pref_rating' in msr && 'pref_score_wsub' in msr.pref_rating) {
            return spk.measurements[def].pref_rating.pref_score_wsub;
        }
        return -10.0;
    }

    function getScoreEqV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('pref_rating_eq' in msr && 'pref_score' in msr.pref_rating_eq) {
            return spk.measurements[def].pref_rating_eq.pref_score;
        }
        return -10.0;
    }

    function getScoreEqWsubV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('pref_rating_eq' in msr && 'pref_score_wsub' in msr.pref_rating_eq) {
            return spk.measurements[def].pref_rating_eq.pref_score_wsub;
        }
        return -10.0;
    }

    function getF3V2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('estimates' in msr && 'ref_3dB' in msr.estimates) {
            return -spk.measurements[def].estimates.ref_3dB;
        }
        return -1000;
    }

    function getF6V2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('estimates' in msr && 'ref_6dB' in msr.estimates) {
            return -spk.measurements[def].estimates.ref_6dB;
        }
        return -1000;
    }

    function getFlatnessV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('estimates' in msr && 'ref_band' in msr.estimates) {
            return -spk.measurements[def].estimates.ref_band;
        }
        return -1000;
    }

    function getSensitivityV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('sensitivity' in msr && 'sensitivity_1m' in msr.sensitivity) {
            return spk.measurements[def].sensitivity.sensitivity_1m;
        }
        return 0.0;
    }

    function getWeightV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('specifications' in msr && 'weight' in msr.specifications) {
            return spk.measurements[def].specifications.weight;
        }
        return 0.0;
    }

    function getSizeWidthV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('specifications' in msr && 'size' in msr.specifications && 'width' in msr.specifications.size) {
            return spk.measurements[def].specifications.size.width;
        }
        return 0.0;
    }

    function getSizeDepthV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('specifications' in msr && 'size' in msr.specifications && 'depth' in msr.specifications.size) {
            return spk.measurements[def].specifications.size.depth;
        }
        return 0.0;
    }

    function getSizeHeightV2(key) {
        const spk = metadata.get(key);
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        if ('specifications' in msr && 'size' in msr.specifications && 'height' in msr.specifications.size) {
            return spk.measurements[def].specifications.size.height;
        }
        return 0.0;
    }

    function getBrandV2(key) {
        const spk = metadata.get(key);
        return spk.brand + ' ' + spk.model;
    }

    // if we have keywords, then sort by quality of match
    if (results != null) {
        return sortChildren2({
            container: metadata,
            score: (k) => {
                if (results.has(k)) {
                    return results.get(k).score;
                }
                return 1000;
            },
            reverse: true,
        });
    }

    if (sorter.by === 'date') {
        return sortChildren2({
            container: metadata,
            score: (k) => getDateV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'score') {
        return sortChildren2({
            container: metadata,
            score: (k) => getScoreV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'scoreEQ') {
        return sortChildren2({
            container: metadata,
            score: (k) => getScoreEqV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'scoreWSUB') {
        return sortChildren2({
            container: metadata,
            score: (k) => getScoreWsubV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'scoreEQWSUB') {
        return sortChildren2({
            container: metadata,
            score: (k) => getScoreEqWsubV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'price') {
        return sortChildren2({
            container: metadata,
            score: (k) => getPriceV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'f3') {
        return sortChildren2({
            container: metadata,
            score: (k) => getF3V2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'f6') {
        return sortChildren2({
            container: metadata,
            score: (k) => getF6V2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'flatness') {
        return sortChildren2({
            container: metadata,
            score: (k) => getFlatnessV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'sensitivity') {
        return sortChildren2({
            container: metadata,
            score: (k) => getSensitivityV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'brand') {
        return sortChildren2({
            container: metadata,
            score: (k) => getBrandV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'weight') {
        return sortChildren2({
            container: metadata,
            score: (k) => getWeightV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'width') {
        return sortChildren2({
            container: metadata,
            score: (k) => getSizeWidthV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'height') {
        return sortChildren2({
            container: metadata,
            score: (k) => getSizeHeightV2(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'depth') {
        return sortChildren2({
            container: metadata,
            score: (k) => getSizeDepthV2(k),
            reverse: sorter.reverse,
        });
    } else {
        console.log('ERROR: unknown sorter ' + sorter.by);
    }

    return metadata;
}

export function isFiltered(item, filter) {
    let shouldShow = true;
    if (filter.reviewer !== undefined && filter.reviewer !== '') {
        let found = true;
        for (const [name, measurement] of Object.entries(item.measurements)) {
            const origin = measurement.origin.toLowerCase();
            let name2 = name.toLowerCase();
            // not ideal
            name2 = name2
                .replace('misc-', '')
                .replace('-sealed', '')
                .replace('-ported', '')
                .replace('-vertical')
                .replace('-horizontal');
            // console.log('debug: name2=' + name2 + ' origin=' + origin + ' filter.reviewer=' + filter.reviewer)
            if (name2 === filter.reviewer.toLowerCase() || origin === filter.reviewer.toLowerCase()) {
                found = false;
                break;
            }
        }
        if (found) {
            shouldShow = false;
        }
    }
    if (shouldShow && filter.quality !== undefined && filter.quality !== '') {
        let found = true;
        for (const [, measurement] of Object.entries(item.measurements)) {
            const quality = measurement.quality.toLowerCase();
            // console.log('filter.quality=' + filter.quality + ' quality=' + quality)
            if (filter.quality !== '' && quality === filter.quality.toLowerCase()) {
                found = false;
                break;
            }
        }
        if (found) {
            shouldShow = false;
        }
    }
    // console.log('debug: post quality ' + shouldShow)
    if (shouldShow && filter.power !== undefined && filter.power !== '' && item.type !== filter.power) {
        shouldShow = false;
    }

    // console.log('debug: post power ' + shouldShow)
    if (shouldShow && filter.shape !== undefined && filter.shape !== '' && item.shape !== filter.shape) {
        shouldShow = false;
    }

    // console.log('debug: post shape ' + shouldShow)
    if (
        shouldShow &&
        filter.brand !== undefined &&
        filter.brand !== '' &&
        item.brand.toLowerCase() !== filter.brand.toLowerCase()
    ) {
        shouldShow = false;
    }

    // console.log('debug: post brand ' + shouldShow + 'filter.price=>>>'+filter.price+'<<<')
    if (shouldShow && filter.price !== undefined && filter.price !== '') {
        // console.log('debug: pre price ' + filter.price)
        if (item.price !== '') {
            let price = parseInt(item.price);
            if (item.amount === 'pair') {
                price /= 2.0;
            }
            switch (filter.price) {
                case 'p100':
                    if (price > 100) {
                        shouldShow = false;
                    }
                    break;
                case 'p200':
                    if (price > 200 || price < 100) {
                        shouldShow = false;
                    }
                    break;
                case 'p300':
                    if (price > 300 || price < 200) {
                        shouldShow = false;
                    }
                    break;
                case 'p400':
                    if (price > 400 || price < 300) {
                        shouldShow = false;
                    }
                    break;
                case 'p500':
                    if (price > 500 || price < 400) {
                        shouldShow = false;
                    }
                    break;
                case 'p1000':
                    if (price > 1000 || price < 500) {
                        shouldShow = false;
                    }
                    break;
                case 'p2000':
                    if (price > 2000 || price < 1000) {
                        shouldShow = false;
                    }
                    break;
                case 'p5000':
                    if (price > 5000 || price < 2000) {
                        shouldShow = false;
                    }
                    break;
                case 'p5000p':
                    if (price <= 5000) {
                        shouldShow = false;
                    }
                    break;
            }
        } else {
            // no known price
            shouldShow = false;
        }
        // console.log('debug: post price ' + shouldShow)
    }

    if (
        shouldShow &&
        ((filter.weightMin !== undefined && filter.weightMin !== '') ||
            (filter.weightMax !== undefined && filter.weightMax !== ''))
    ) {
        var weightMin = parseInt(filter.weightMin);
        if (isNaN(weightMin)) {
            weightMin = -1;
        }
        var weightMax = parseInt(filter.weightMax);
        if (isNaN(weightMax)) {
            weightMax = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('specifications' in msr && 'weight' in msr.specifications) {
            let weight = parseInt(msr.specifications.weight);
            // console.debug('pre weight ' + weightMin + ', ' + weightMax + ' and item.weight=' + msr.specifications.weight);
            if (isNaN(weight)) {
                shouldShow = false;
            } else {
                if (weight > weightMax || weight < weightMin) {
                    shouldShow = false;
                }
            }
        } else {
            // no known weight
            shouldShow = false;
        }
        // console.debug('debug: post weight ' + shouldShow);
    }

    if (
        shouldShow &&
        ((filter.heightMin !== undefined && filter.heightMin !== '') ||
            (filter.heightMax !== undefined && filter.heightMax !== ''))
    ) {
        var heightMin = parseInt(filter.heightMin);
        if (isNaN(heightMin)) {
            heightMin = -1;
        }
        var heightMax = parseInt(filter.heightMax);
        if (isNaN(heightMax)) {
            heightMax = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('specifications' in msr && 'size' in msr.specifications && 'height' in msr.specifications.size) {
            let height = parseInt(msr.specifications.size.height);
            // console.debug('pre height ' + heightMin + ', ' + heightMax + ' and item.height=' + msr.specifications.size.height);
            if (isNaN(height)) {
                shouldShow = false;
            } else {
                if (height > heightMax || height < heightMin) {
                    shouldShow = false;
                }
            }
        } else {
            // no known height
            shouldShow = false;
        }
        // console.debug('debug: post height ' + shouldShow);
    }

    if (
        shouldShow &&
        ((filter.depthMin !== undefined && filter.depthMin !== '') || (filter.depthMax !== undefined && filter.depthMax !== ''))
    ) {
        var depthMin = parseInt(filter.depthMin);
        if (isNaN(depthMin)) {
            depthMin = -1;
        }
        var depthMax = parseInt(filter.depthMax);
        if (isNaN(depthMax)) {
            depthMax = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('specifications' in msr && 'size' in msr.specifications && 'depth' in msr.specifications.size) {
            let depth = parseInt(msr.specifications.size.depth);
            // console.debug('pre depth ' + depthMin + ', ' + depthMax + ' and item.depth=' + msr.specifications.size.depth);
            if (isNaN(depth)) {
                shouldShow = false;
            } else {
                if (depth > depthMax || depth < depthMin) {
                    shouldShow = false;
                }
            }
        } else {
            // no known depth
            shouldShow = false;
        }
        // console.debug('debug: post depth ' + shouldShow);
    }

    if (
        shouldShow &&
        ((filter.widthMin !== undefined && filter.widthMin !== '') || (filter.widthMax !== undefined && filter.widthMax !== ''))
    ) {
        var widthMin = parseInt(filter.widthMin);
        if (isNaN(widthMin)) {
            widthMin = -1;
        }
        var widthMax = parseInt(filter.widthMax);
        if (isNaN(widthMax)) {
            widthMax = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('specifications' in msr && 'size' in msr.specifications && 'width' in msr.specifications.size) {
            let width = parseInt(msr.specifications.size.width);
            // console.debug('pre width ' + widthMin + ', ' + widthMax + ' and item.width=' + msr.specifications.size.width);
            if (isNaN(width)) {
                shouldShow = false;
            } else {
                if (width > widthMax || width < widthMin) {
                    shouldShow = false;
                }
            }
        } else {
            // no known width
            shouldShow = false;
        }
        // console.debug('debug: post width ' + shouldShow);
    }

    return shouldShow;
}

export function isSearch(key, results, minScore, keywords) {
    // console.log('Starting isSearch with key='+key+' minscore='+minScore+' keywords='+keywords);

    let shouldShow = true;
    if (keywords === '' || results === undefined) {
        // console.log('shouldShow is true');
        return shouldShow;
    }

    if (!results.has(key)) {
        // console.log('shouldShow is false (no key '+key+')');
        return false;
    }

    const result = results.get(key);
    const imeta = result.item.speaker;
    const score = result.score;

    if (minScore < Math.pow(10, -15)) {
        const isExact = imeta.model.toLowerCase().includes(keywords.toLowerCase());
        // console.log('isExact ' + isExact + ' model ' + imeta.model.toLowerCase() + ' keywords ' + keywords.toLowerCase());
        // we have an exact match, only shouldShow other exact matches
        if (score >= Math.pow(10, -15) && !isExact) {
            // console.log('filtered out (minscore)' + score);
            shouldShow = false;
        }
    } else {
        // only partial match
        if (score > minScore * 10) {
            // console.log('filtered out (score=' + score + 'minscore=' + minScore + ')');
            shouldShow = false;
        }
        // else { console.log('not filtered out (score=' + score + 'minscore=' + minScore + ')'); }
    }
    return shouldShow;
}

function isWithinPage(count, pagination) {
    const page = pagination.page;
    const size = pagination.count;
    if (!pagination.active || (count >= (page - 1) * size && count <= page * size)) {
        return true;
    }
    return false;
}

export function search(data, params) {
    const fuse = new Fuse(
        // Fuse take a list not a map
        [...data].map((item) => ({ key: item[0], speaker: item[1] })),
        {
            isCaseSensitive: false,
            matchAllTokens: true,
            findAllMatches: true,
            minMatchCharLength: 2,
            keys: ['speaker.brand', 'speaker.model', 'speaker.type', 'speaker.shape'],
            treshhold: 0.2,
            distance: 10,
            includeScore: true,
            useExtendedSearch: false,
            shouldSort: true,
        }
    );

    const sorter = params[0];
    const filters = params[1];
    const keywords = params[2];
    const pagination = params[3];
    let resultsFullText = null;
    let minScore = 1;
    if (keywords !== '') {
        const fuse_results = fuse.search(keywords);
        // console.log('searching with keywords: '+keywords+' #matches: '+fuse_results.length);
        if (fuse_results.length > 0) {
            // minScore
            for (const spk in fuse_results) {
                if (fuse_results[spk].score < minScore) {
                    minScore = fuse_results[spk].score;
                }
            }
        }
        resultsFullText = new Map(fuse_results.map((obj) => [obj.item.key, obj]));
    }

    const resultsFiltered = [];
    let currentDisplay = 0;
    let maxDisplay = 0;
    const targetDisplay = pagination.count;
    sortMetadata2(data, sorter, resultsFullText).forEach((key, index) => {
        const speaker = data.get(key);
        const testFiltered = isFiltered(speaker, filters);
        const testKeywords = isSearch(key, resultsFullText, minScore, keywords);
        const withinPage = isWithinPage(currentDisplay, pagination);
        // console.debug(speaker.brand+' '+speaker.model+' '+testFiltered+' '+testKeywords+' '+withinPage);
        if (currentDisplay < targetDisplay) {
            if (testFiltered && testKeywords && withinPage && currentDisplay < targetDisplay) {
                resultsFiltered.push(key);
                currentDisplay += 1;
                maxDisplay += 1;
            } else if (testFiltered && testKeywords) {
                maxDisplay += 1;
            }
        }
    });
    return [maxDisplay, resultsFiltered];
}

export function process(data, params, printer) {
    const [maxResults, results] = search(data, params);
    const fragment = new DocumentFragment();
    results.forEach((key, index) => {
        const speaker = data.get(key);
        const current = printer(key, index, speaker);
        show(current);
        fragment.appendChild(current);
    });
    return [maxResults, fragment];
}

export function setupEventListener(metadata, speaker2html, mainDiv) {
    function update(element, urlParameter, parentDiv) {
        const url = new URL(window.location);
        if (element.id === 'searchInput' && element.value) {
            // disable search for short words?
            // if (element.value.length <= 2) {
            //   return;
            // }
            // remove pagination if it was not a search before
            if (!url.searchParams.has('search')) {
                url.searchParams.set('page', 1);
            }
        }
        if (element.id === 'sortReverse') {
            let reverseValue = 'false';
            if (element.checked) {
                reverseValue = 'true';
            }
            url.searchParams.set(urlParameter, reverseValue);
            // console.log('Info: '+urlParameter + ' changed to ' + element.value);
        } else {
            if (element.value !== '') {
                url.searchParams.set(urlParameter, element.value);
                // console.log('Info: '+urlParameter + ' changed to ' + element.value);
            } else {
                url.searchParams.delete(urlParameter);
                // console.log('Info: '+urlParameter + ' removed');
            }
        }
        window.history.pushState({}, '', url);
        const params = urlParameters2Sort(url);
        // printParams(params);
        const fragment = process(metadata, params, speaker2html);
        // very slow if long list
        while (parentDiv.firstChild) {
            parentDiv.removeChild(parentDiv.firstChild);
        }
        parentDiv.appendChild(fragment);
        show(parentDiv);
    }

    parametersMapping.forEach((parameter) => {
        const selectorName = parameter.selectorName;
        const urlParameter = parameter.urlParameter;
        const eventType = parameter.eventType;
        let element = document.querySelector(selectorName);
        if (element) {
            element.addEventListener(eventType, () => update(element, urlParameter, mainDiv));
        } else {
            console.log('Error: Element ' + selectorName + ' not found');
        }
    });
}
