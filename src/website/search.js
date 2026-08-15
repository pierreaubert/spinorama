// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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
import { show, validShape } from './misc.js';
import { pagination } from './pagination.js';

const parametersMapping = [
    // filters
    { selectorName: '#selectReviewer', urlParameter: 'reviewer', eventType: 'change' },
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
    { selectorName: '#inputF3Min', urlParameter: 'f3Min', eventType: 'change' },
    { selectorName: '#inputF3Max', urlParameter: 'f3Max', eventType: 'change' },
    { selectorName: '#inputF6Min', urlParameter: 'f6Min', eventType: 'change' },
    { selectorName: '#inputF6Max', urlParameter: 'f6Max', eventType: 'change' },
    { selectorName: '#inputSensitivityMin', urlParameter: 'sensitivityMin', eventType: 'change' },
    { selectorName: '#inputSensitivityMax', urlParameter: 'sensitivityMax', eventType: 'change' },
    { selectorName: '#inputImpedanceMin', urlParameter: 'impedanceMin', eventType: 'change' },
    { selectorName: '#inputImpedanceMax', urlParameter: 'impedanceMax', eventType: 'change' },
    { selectorName: '#inputLfxMin', urlParameter: 'lfxMin', eventType: 'change' },
    { selectorName: '#inputLfxMax', urlParameter: 'lfxMax', eventType: 'change' },
    { selectorName: '#inputSplMin', urlParameter: 'splMin', eventType: 'change' },
    { selectorName: '#inputSplMax', urlParameter: 'splMax', eventType: 'change' },
    { selectorName: '#inputBandwidthMin', urlParameter: 'bandwidthMin', eventType: 'change' },
    { selectorName: '#inputBandwidthMax', urlParameter: 'bandwidthMax', eventType: 'change' },
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
    'fullTextSearch',
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

/*
function printParams(params) {
    const [sorter, filter, keywords, pagination] = [...params];
    console.log('  sorter: ' + sorter.by + ' reverse: ' + sorter.reverse);
    console.log(
        '  filter:' +
            ' brand=' +
            filter.brand +
            ' power=' +
            filter.power +
            ' quality=' +
            filter.quality +
            ' ' +
            filter.priceMin +
            ' <=price<= ' +
            filter.priceMax +
            ' reviewer=' +
            filter.reviewer +
            ' shape=' +
            filter.shape
    );
    console.log(' keywords=' + keywords.toString());
    console.log(' pagination: page=' + pagination.page);
}
*/

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
                console.error('Selector ' + selectorName + ' is unknown!');
            }
        } else {
            console.error('Sort function ' + sortParams + ' is unknown!');
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
        console.error('Selector ' + selectorName + ' is unknown!');
    }

    return sorter;
}

function filtersParameters2Sort(url) {
    const filters = {
        brand: '',
        power: '',
        quality: [],
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
        f3Min: '',
        f3Max: '',
        f6Min: '',
        f6Max: '',
        sensitivityMin: '',
        sensitivityMax: '',
        impedanceMin: '',
        impedanceMax: '',
        lfxMin: '',
        lfxMax: '',
        splMin: '',
        splMax: '',
        bandwidthMin: '',
        bandwidthMax: '',
    };
    for (const filterName of Object.keys(filters)) {
        if (filterName === 'quality') {
            continue;
        }
        if (url.searchParams.has(filterName)) {
            filters[filterName] = url.searchParams.get(filterName);
            const selectorName = urlToSelectorName.get(filterName);
            let selector = document.querySelector(selectorName);
            if (selector) {
                selector.value = filters[filterName];
            } else {
                console.error('Filter selector ' + filterName + ' is unknown!');
            }
        }
    }
    if (url.searchParams.has('quality')) {
        const qualityParam = url.searchParams.get('quality');
        filters.quality = qualityParam.split(',').filter((v) => v !== '');
        const checkboxes = document.querySelectorAll('.qualityCheckbox');
        checkboxes.forEach((cb) => {
            cb.checked = filters.quality.includes(cb.value);
        });
    }
    return filters;
}

function keywordsParameters2Sort(url) {
    let keywords = '';
    if (url.searchParams.has('search')) {
        keywords = url.searchParams
            .get('search')
            .toString()
            .replace(/[^a-zA-Z0-9&]/g, ' ');
        const selectorName = urlToSelectorName.get('search');
        let selector = document.querySelector(selectorName);
        if (selector) {
            selector.value = keywords;
        } else {
            console.error('Search selector ' + selectorName + ' is unknown!');
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
        if (!isNaN(page) && page > 0) {
            pagination.page = page;
            pagination.active = true;
        } else {
            console.warning('Ignored parameter page that must be a positive integer (got ' + page + '!');
        }
    }
    if (url.searchParams.has('count')) {
        const count = parseInt(url.searchParams.get('count'));
        if (!isNaN(count) && count > 1) {
            pagination.count = count;
            pagination.active = true;
        } else {
            console.warning('Ignored parameter count that must be an integer greater than 1 (got ' + count + '!');
        }
    }
    return pagination;
}

export function urlParameters2Sort(url) {
    const sorter = sortParameters2Sort(url);
    const filters = filtersParameters2Sort(url);
    const keywords = keywordsParameters2Sort(url);
    const pagination = paginationParameters2Sort(url);

    // if we have keywords to search for then give priority for search
    // but only if the sort parameter is not explicitly set to something other than 'date' (default)
    if (keywords !== '' && sorter.by === 'date') {
        sorter.by = 'fullTextSearch';
        sorter.reverse = true;
    }
    return [sorter, filters, keywords, pagination];
}

export function sortMetadata2(metadata, sorter, results) {
    const sortChildren = ({ container, score, reverse }) => {
        // console.log('sorting2 by '+score)
        const items = [...container.keys()];
        if (reverse) {
            items.sort((a, b) => {
                const sa = score(a);
                const sb = score(b);
                if (sa === sb) {
                    return a < b ? -1 : a > b ? 1 : 0;
                }
                return sa - sb;
            });
        } else {
            items.sort((a, b) => {
                const sa = score(a);
                const sb = score(b);
                if (sa === sb) {
                    return b < a ? -1 : b > a ? 1 : 0;
                }
                return sb - sa;
            });
        }
        // console.table(items)
        return items;
    };

    function getDate(key) {
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

    function getPrice(key) {
        const spk = metadata.get(key);
        let price = parseFloat(spk.price);
        if (!isNaN(price)) {
            if (!spk.amount || spk?.amount === 'pair') {
                price /= 2;
            }
            return price;
        }
        return -1;
    }

    // All getScore* helpers must tolerate speakers with:
    //   - no default_measurement
    //   - no measurements object
    //   - missing pref_rating / pref_rating_eq
    //   - missing specific score fields
    //   - shape not in validShape (e.g. inwall, outdoor, cbt — these have
    //     CEA2034 data but the card UI displays *** instead of the score, so
    //     we sort them to the end too, matching what the user sees on the card)
    // A missing/invalid score returns -10 so those speakers sort to the end
    // when used as the key for a descending sort.
    function hasDisplayedScore(key) {
        const spk = metadata.get(key);
        if (!spk) return false;
        // Headphones always display their score
        if (spk.kind === 'headphone') return true;
        return validShape.has(spk.shape);
    }

    function getScore(key) {
        if (!hasDisplayedScore(key)) return -10;
        const spk = metadata.get(key);
        // Headphones store scores at the top level
        if (spk && spk.kind === 'headphone' && typeof spk.score === 'number') {
            return spk.score;
        }
        const msr = defMsr(key);
        const score = msr && msr.pref_rating ? msr.pref_rating.pref_score : undefined;
        return typeof score === 'number' ? score : -10;
    }

    function getScoreWsub(key) {
        if (!hasDisplayedScore(key)) return -10;
        const spk = metadata.get(key);
        // Headphones don't have a wsub score
        if (spk && spk.kind === 'headphone') return -10;
        const msr = defMsr(key);
        const score = msr && msr.pref_rating ? msr.pref_rating.pref_score_wsub : undefined;
        return typeof score === 'number' ? score : -10;
    }

    function getScoreEq(key) {
        if (!hasDisplayedScore(key)) return -10;
        const spk = metadata.get(key);
        // Headphones store EQ scores at the top level
        if (spk && spk.kind === 'headphone' && typeof spk.score_eq === 'number') {
            return spk.score_eq;
        }
        const msr = defMsr(key);
        const score = msr && msr.pref_rating_eq ? msr.pref_rating_eq.pref_score : undefined;
        return typeof score === 'number' ? score : -10;
    }

    function getScoreEqWsub(key) {
        if (!hasDisplayedScore(key)) return -10;
        const spk = metadata.get(key);
        // Headphones don't have a wsub score
        if (spk && spk.kind === 'headphone') return -10;
        const msr = defMsr(key);
        const score = msr && msr.pref_rating_eq ? msr.pref_rating_eq.pref_score_wsub : undefined;
        return typeof score === 'number' ? score : -10;
    }

    // Helper: return the default measurement object for a speaker, or null if
    // the speaker has no default_measurement or no matching measurements entry.
    function defMsr(key) {
        const spk = metadata.get(key);
        if (!spk) return null;
        const def = spk.default_measurement;
        if (!def || !spk.measurements) return null;
        const msr = spk.measurements[def];
        return msr || null;
    }

    function getF3(key) {
        const msr = defMsr(key);
        const v = msr && msr.estimates ? msr.estimates.ref_3dB : undefined;
        return typeof v === 'number' ? -v : -1000;
    }

    function getF6(key) {
        const msr = defMsr(key);
        const v = msr && msr.estimates ? msr.estimates.ref_6dB : undefined;
        return typeof v === 'number' ? -v : -1000;
    }

    function getFlatness(key) {
        const msr = defMsr(key);
        const v = msr && msr.estimates ? msr.estimates.ref_band : undefined;
        return typeof v === 'number' ? -v : -1000;
    }

    function getSensitivity(key) {
        const msr = defMsr(key);
        const cs = msr?.computed_sensitivity ?? msr?.sensitivity;
        const v = cs?.sensitivity_1m;
        return typeof v === 'number' ? v : 0.0;
    }

    function getWeight(key) {
        const msr = defMsr(key);
        const v = msr && msr.specifications ? msr.specifications.weight : undefined;
        return typeof v === 'number' ? v : 0.0;
    }

    function getSizeWidth(key) {
        const msr = defMsr(key);
        const v = msr && msr.specifications && msr.specifications.size ? msr.specifications.size.width : undefined;
        return typeof v === 'number' ? v : 0.0;
    }

    function getSizeDepth(key) {
        const msr = defMsr(key);
        const v = msr && msr.specifications && msr.specifications.size ? msr.specifications.size.depth : undefined;
        return typeof v === 'number' ? v : 0.0;
    }

    function getSizeHeight(key) {
        const msr = defMsr(key);
        const v = msr && msr.specifications && msr.specifications.size ? msr.specifications.size.height : undefined;
        return typeof v === 'number' ? v : 0.0;
    }

    function getBrand(key) {
        const spk = metadata.get(key);
        if (!spk) return '';
        return (spk.brand || '') + ' ' + (spk.model || '');
    }

    function getFullTextSearch(key, fts) {
        const spk = fts.get(key);
        if (!spk || !spk.score) {
            return 100;
        }
        // console.debug('speaker '+key+' score='+spk.score);
        return spk.score;
    }

    if (sorter.by === 'date') {
        return sortChildren({
            container: metadata,
            score: (k) => getDate(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'score') {
        return sortChildren({
            container: metadata,
            score: (k) => getScore(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'scoreEQ') {
        return sortChildren({
            container: metadata,
            score: (k) => getScoreEq(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'scoreWSUB') {
        return sortChildren({
            container: metadata,
            score: (k) => getScoreWsub(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'scoreEQWSUB') {
        return sortChildren({
            container: metadata,
            score: (k) => getScoreEqWsub(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'price') {
        return sortChildren({
            container: metadata,
            score: (k) => getPrice(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'f3') {
        return sortChildren({
            container: metadata,
            score: (k) => getF3(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'f6') {
        return sortChildren({
            container: metadata,
            score: (k) => getF6(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'flatness') {
        return sortChildren({
            container: metadata,
            score: (k) => getFlatness(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'sensitivity') {
        return sortChildren({
            container: metadata,
            score: (k) => getSensitivity(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'brand') {
        return sortChildren({
            container: metadata,
            score: (k) => getBrand(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'weight') {
        return sortChildren({
            container: metadata,
            score: (k) => getWeight(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'width') {
        return sortChildren({
            container: metadata,
            score: (k) => getSizeWidth(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'height') {
        return sortChildren({
            container: metadata,
            score: (k) => getSizeHeight(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'depth') {
        return sortChildren({
            container: metadata,
            score: (k) => getSizeDepth(k),
            reverse: sorter.reverse,
        });
    } else if (sorter.by === 'fullTextSearch') {
        return sortChildren({
            container: metadata,
            score: (k) => getFullTextSearch(k, results),
            reverse: sorter.reverse,
        });
    } else {
        console.error('Unknown sorter ' + sorter.by);
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
    if (shouldShow && Array.isArray(filter.quality) && filter.quality.length > 0) {
        let found = false;
        const qualitySet = new Set(filter.quality.map((q) => q.toLowerCase()));
        for (const [, measurement] of Object.entries(item.measurements)) {
            const quality = measurement.quality.toLowerCase();
            if (qualitySet.has(quality)) {
                found = true;
                break;
            }
        }
        if (!found) {
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

    // console.log('debug: before price ' + shouldShow + 'min=>>>'+filter.priceMin+'<<< max=>>>'+filter.priceMax+'<<<')
    if (
        shouldShow &&
        ((filter.priceMin !== undefined && filter.priceMin !== '') || (filter.priceMax !== undefined && filter.priceMax !== ''))
    ) {
        var priceMin = parseFloat(filter.priceMin);
        if (isNaN(priceMin)) {
            priceMin = -1;
        }
        var priceMax = parseFloat(filter.priceMax);
        if (isNaN(priceMax)) {
            priceMax = Number.MAX_SAFE_INTEGER;
        }
        if (item?.price !== '') {
            let price = parseFloat(item.price);
            if (isNaN(price)) {
                shouldShow = false;
            } else {
                if (!item.amount || item?.amount === 'pair') {
                    price /= 2.0;
                }
                if (price > priceMax || price < priceMin) {
                    shouldShow = false;
                }
            }
        } else {
            // no known price
            shouldShow = false;
        }
        // console.debug('debug: post price ' + shouldShow);
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

    if (
        shouldShow &&
        ((filter.f3Min !== undefined && filter.f3Min !== '') || (filter.f3Max !== undefined && filter.f3Max !== ''))
    ) {
        var f3Min = parseFloat(filter.f3Min);
        if (isNaN(f3Min)) {
            f3Min = -1;
        }
        var f3Max = parseFloat(filter.f3Max);
        if (isNaN(f3Max)) {
            f3Max = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('estimates' in msr && 'ref_3dB' in msr.estimates) {
            let f3 = parseFloat(msr.estimates.ref_3dB);
            if (isNaN(f3)) {
                shouldShow = false;
            } else {
                if (f3 > f3Max || f3 < f3Min) {
                    shouldShow = false;
                }
            }
        } else {
            shouldShow = false;
        }
    }

    if (
        shouldShow &&
        ((filter.f6Min !== undefined && filter.f6Min !== '') || (filter.f6Max !== undefined && filter.f6Max !== ''))
    ) {
        var f6Min = parseFloat(filter.f6Min);
        if (isNaN(f6Min)) {
            f6Min = -1;
        }
        var f6Max = parseFloat(filter.f6Max);
        if (isNaN(f6Max)) {
            f6Max = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('estimates' in msr && 'ref_6dB' in msr.estimates) {
            let f6 = parseFloat(msr.estimates.ref_6dB);
            if (isNaN(f6)) {
                shouldShow = false;
            } else {
                if (f6 > f6Max || f6 < f6Min) {
                    shouldShow = false;
                }
            }
        } else {
            shouldShow = false;
        }
    }

    if (
        shouldShow &&
        ((filter.sensitivityMin !== undefined && filter.sensitivityMin !== '') ||
            (filter.sensitivityMax !== undefined && filter.sensitivityMax !== ''))
    ) {
        var sensitivityMin = parseFloat(filter.sensitivityMin);
        if (isNaN(sensitivityMin)) {
            sensitivityMin = -1;
        }
        var sensitivityMax = parseFloat(filter.sensitivityMax);
        if (isNaN(sensitivityMax)) {
            sensitivityMax = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        const cs = msr.computed_sensitivity ?? msr.sensitivity;
        if (cs && ('sensitivity_1m' in cs || 'computed' in cs)) {
            let sensitivity = parseFloat(cs.sensitivity_1m ?? cs.computed);
            if (isNaN(sensitivity)) {
                shouldShow = false;
            } else {
                if (sensitivity > sensitivityMax || sensitivity < sensitivityMin) {
                    shouldShow = false;
                }
            }
        } else {
            shouldShow = false;
        }
    }

    if (
        shouldShow &&
        ((filter.impedanceMin !== undefined && filter.impedanceMin !== '') ||
            (filter.impedanceMax !== undefined && filter.impedanceMax !== ''))
    ) {
        var impedanceMin = parseInt(filter.impedanceMin);
        if (isNaN(impedanceMin)) {
            impedanceMin = -1;
        }
        var impedanceMax = parseInt(filter.impedanceMax);
        if (isNaN(impedanceMax)) {
            impedanceMax = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('specifications' in msr && 'impedance' in msr.specifications) {
            let impedance = parseInt(msr.specifications.impedance);
            if (isNaN(impedance)) {
                shouldShow = false;
            } else {
                if (impedance > impedanceMax || impedance < impedanceMin) {
                    shouldShow = false;
                }
            }
        } else {
            shouldShow = false;
        }
    }

    if (
        shouldShow &&
        ((filter.lfxMin !== undefined && filter.lfxMin !== '') || (filter.lfxMax !== undefined && filter.lfxMax !== ''))
    ) {
        var lfxMin = parseInt(filter.lfxMin);
        if (isNaN(lfxMin)) {
            lfxMin = -1;
        }
        var lfxMax = parseInt(filter.lfxMax);
        if (isNaN(lfxMax)) {
            lfxMax = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('pref_rating' in msr && 'lfx_hz' in msr.pref_rating) {
            let lfx = parseInt(msr.pref_rating.lfx_hz);
            if (isNaN(lfx)) {
                shouldShow = false;
            } else {
                if (lfx > lfxMax || lfx < lfxMin) {
                    shouldShow = false;
                }
            }
        } else {
            shouldShow = false;
        }
    }

    if (
        shouldShow &&
        ((filter.splMin !== undefined && filter.splMin !== '') || (filter.splMax !== undefined && filter.splMax !== ''))
    ) {
        var splMin = parseInt(filter.splMin);
        if (isNaN(splMin)) {
            splMin = -1;
        }
        var splMax = parseInt(filter.splMax);
        if (isNaN(splMax)) {
            splMax = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('specifications' in msr && 'SPL' in msr.specifications && 'peak' in msr.specifications.SPL) {
            let spl = parseInt(msr.specifications.SPL.peak);
            if (isNaN(spl)) {
                shouldShow = false;
            } else {
                if (spl > splMax || spl < splMin) {
                    shouldShow = false;
                }
            }
        } else {
            shouldShow = false;
        }
    }

    if (
        shouldShow &&
        ((filter.bandwidthMin !== undefined && filter.bandwidthMin !== '') ||
            (filter.bandwidthMax !== undefined && filter.bandwidthMax !== ''))
    ) {
        var bandwidthMin = parseFloat(filter.bandwidthMin);
        if (isNaN(bandwidthMin)) {
            bandwidthMin = -1;
        }
        var bandwidthMax = parseFloat(filter.bandwidthMax);
        if (isNaN(bandwidthMax)) {
            bandwidthMax = Number.MAX_SAFE_INTEGER;
        }
        const msr = item.measurements[item.default_measurement];
        if ('estimates' in msr && 'ref_band' in msr.estimates) {
            let bandwidth = parseFloat(msr.estimates.ref_band);
            if (isNaN(bandwidth)) {
                shouldShow = false;
            } else {
                if (bandwidth > bandwidthMax || bandwidth < bandwidthMin) {
                    shouldShow = false;
                }
            }
        } else {
            shouldShow = false;
        }
    }

    return shouldShow;
}

export function isSearch(key, results, minScore, keywords) {
    // console.debug('Starting isSearch with key='+key+' minscore='+minScore+' keywords='+keywords);
    let shouldShow = true;
    if (keywords === '' || results === undefined) {
        return shouldShow;
    }

    if (!results.has(key)) {
        return false;
    }

    const result = results.get(key);
    const score = result.score;

    // `results` is a Map (size, not length). When there is an exact match
    // somewhere (minScore ≈ 0), drop entries with a clearly worse score so we
    // don't show unrelated speakers matched via partial type/shape fields.
    if (minScore < Math.pow(10, -6)) {
        // we have an exact match → only show other exact/near-exact matches
        if (score >= 0.01 && results.size > 5) {
            shouldShow = false;
        }
    } else {
        // only partial match
        if (score > minScore * 100) {
            shouldShow = false;
        }
    }
    return shouldShow;
}

export function isWithinPage(position, pagination) {
    const page = pagination.page;
    const count = pagination.count;
    if (!pagination.active || (position >= (page - 1) * count && position < page * count)) {
        return true;
    }
    return false;
}

export function rank1(fuse, brands, models, word) {
    const normalized = word.trim().toLowerCase();
    // Known brand/model tokens should also match suffixed variants, e.g.
    // searching for "R3" must include both "R3" and "R3 Meta".
    const query = brands.has(normalized) || models.has(normalized) ? `^${normalized}` : normalized;
    const results = fuse.search(query);
    return results;
}

export function rank2(fuse, brands, models, words) {
    // perfect world
    if (brands.has(words[0]) && brands.has(words[1])) {
        const query_exact = {
            $and: [{ 'speaker.brand': "'" + words[0] }, { 'speaker.brand': "'" + words[1] }],
        };
        const results_exact = fuse.search(query_exact);
        if (results_exact.length > 0) {
            return results_exact;
        }
    }
    if (brands.has(words[0]) && models.has(words[1])) {
        const query_exact = {
            $and: [{ 'speaker.brand': "'" + words[0] }, { 'speaker.model': "'" + words[1] }],
        };
        const results_exact = fuse.search(query_exact);
        if (results_exact.length > 0) {
            return results_exact;
        }
    }
    if (models.has(words[0]) && models.has(words[1])) {
        const query_exact = {
            $and: [{ 'speaker.models': "'" + words[0] }, { 'speaker.model': "'" + words[1] }],
        };
        const results_exact = fuse.search(query_exact);
        if (results_exact.length > 0) {
            return results_exact;
        }
    }
    // concat 2 words and see if that is a brand or a model
    const concat1 = words[0] + ' ' + words[1];
    if (brands.has(concat1) || models.has(concat1)) {
        return rank1(fuse, brands, models, concat1);
    }
    const concat2 = words[0] + words[1];
    if (brands.has(concat2) || models.has(concat2)) {
        return rank1(fuse, brands, models, concat2);
    }
    // try a normal query
    const queryBB = {
        $and: [{ 'speaker.brand': words[0] }, { 'speaker.brands': words[1] }],
    };
    const resultsBB = fuse.search(queryBB);
    if (resultsBB.length > 0) {
        return resultsBB;
    }
    const queryMM = {
        $and: [{ 'speaker.model': words[0] }, { 'speaker.model': words[1] }],
    };
    const resultsMM = fuse.search(queryMM);
    if (resultsMM.length > 0) {
        return resultsMM;
    }
    const queryBM = {
        $and: [{ 'speaker.brand': words[0] }, { 'speaker.model': words[1] }],
    };
    const resultsBM = fuse.search(queryBM);
    if (resultsBM.length > 0) {
        return resultsBM;
    }
    return fuse.search(words.join(' '));
}

export function rankN(fuse, brands, models, words) {
    if (words.length === 2) {
        return rank2(fuse, brands, models, words);
    }
    const concat01 = words[0] + ' ' + words[1];
    if (brands.has(concat01) || models.has(concat01)) {
        const condensed = [concat01].concat(words.slice(2));
        return rankN(fuse, brands, models, condensed);
    }
    const concat12 = words[1] + ' ' + words[2];
    if (brands.has(concat12) || models.has(concat12)) {
        const condensed = [words[0], concat12].concat(words.slice(3));
        return rankN(fuse, brands, models, condensed);
    }
    if (brands.has(words[0])) {
        const condensed = [words[0], words.slice(1).join(' ')];
        return rank2(fuse, brands, models, condensed);
    }
    return fuse.search(words.join(' '));
}

function rankLoose(fuse, words) {
    // Each word must match somewhere in brand or model (as a substring).
    // This handles cases like "KEF Q Meta" matching "KEF Q150 Meta".
    const query = {
        $and: words.map((w) => ({
            $or: [{ 'speaker.brand': "'" + w }, { 'speaker.model': "'" + w }],
        })),
    };
    return fuse.search(query);
}

export function rank(fuse, brands, models, keywords) {
    let results = null;
    let minScore = 100;
    let resultsFullText = null;
    if (keywords !== '') {
        const words = keywords.trim().split(' ');
        if (words.length === 1) {
            results = rank1(fuse, brands, models, words[0]);
        } else if (words.length === 2) {
            results = rank2(fuse, brands, models, words);
        } else {
            results = rankN(fuse, brands, models, words);
        }
        // If strict search found nothing, try a looser search where each
        // word independently matches brand or model.
        if (results.length === 0 && words.length > 1) {
            results = rankLoose(fuse, words);
        }
        if (results.length > 0) {
            for (const spk in results) {
                if (results[spk].score < minScore) {
                    minScore = results[spk].score;
                }
            }
        }
        resultsFullText = new Map(results.map((obj) => [obj.item.key, obj]));
    }
    return [minScore, resultsFullText];
}

export function search(data, params) {
    const brands = new Set();
    const models = new Set();
    // (v, k)
    data.forEach((v) => {
        brands.add(v['brand'].toLowerCase());
        models.add(v['model'].toLowerCase());
    });
    const fuse_exact = new Fuse(
        // Fuse take a list not a map
        [...data].map((item) => ({ key: item[0], speaker: item[1] })),
        {
            isCaseSensitive: false,
            matchAllTokens: true,
            findAllMatches: true,
            minMatchCharLength: 2,
            keys: ['speaker.brand', 'speaker.model', 'speaker.type', 'speaker.shape'],
            includeScore: true,
            shouldSort: false,
            treshhold: 0,
            useExtendedSearch: true,
        }
    );

    const sorter = params[0];
    const filters = params[1];
    const keywords = params[2];
    const pagination = params[3];
    const [minScore, resultsFullText] = rank(fuse_exact, brands, models, keywords);

    const resultsFiltered = [];
    let maxDisplay = 0;
    sortMetadata2(data, sorter, resultsFullText).forEach((key) => {
        const speaker = data.get(key);
        const testFiltered = isFiltered(speaker, filters);
        const testKeywords = isSearch(key, resultsFullText, minScore, keywords);
        if (testFiltered && testKeywords) {
            if (isWithinPage(maxDisplay, pagination)) {
                resultsFiltered.push(key);
            }
            maxDisplay += 1;
        }
    });
    // console.debug('search for: >' + keywords + '< found #' + maxDisplay);
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
            // console.debug('Info: '+urlParameter + ' changed to ' + element.value);
        } else {
            if (element.value !== '') {
                url.searchParams.set(urlParameter, element.value);
                url.searchParams.set('page', 1);
                // console.debug('Info: '+urlParameter + ' changed to ' + element.value);
            } else {
                url.searchParams.delete(urlParameter);
                // console.debug('Info: '+urlParameter + ' removed');
                url.searchParams.set('page', 1);
            }
        }
        window.history.pushState({}, '', url);
        const params = urlParameters2Sort(url);
        // printParams(params);
        const [maxResults, fragment] = process(metadata, params, speaker2html);
        // very slow if long list
        while (parentDiv.firstChild) {
            parentDiv.removeChild(parentDiv.firstChild);
        }
        if (fragment) {
            parentDiv.appendChild(fragment);
            pagination(maxResults);
        }
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
            console.error('Element ' + selectorName + ' not found');
        }
    });

    const qualityCheckboxes = document.querySelectorAll('.qualityCheckbox');
    qualityCheckboxes.forEach((cb) => {
        cb.addEventListener('change', () => {
            const url = new URL(window.location);
            const selected = [...document.querySelectorAll('.qualityCheckbox:checked')].map((c) => c.value);
            if (selected.length > 0) {
                url.searchParams.set('quality', selected.join(','));
            } else {
                url.searchParams.delete('quality');
            }
            url.searchParams.set('page', 1);
            window.history.pushState({}, '', url);
            const params = urlParameters2Sort(url);
            const [maxResults, fragment] = process(metadata, params, speaker2html);
            while (mainDiv.firstChild) {
                mainDiv.removeChild(mainDiv.firstChild);
            }
            if (fragment) {
                mainDiv.appendChild(fragment);
                pagination(maxResults);
            }
            show(mainDiv);
        });
    });
}
