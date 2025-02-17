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

import { readFileSync } from 'fs';
import { beforeAll, describe, expect, it } from 'vitest';

import { getID } from './misc.js';
import { isWithinPage, urlParameters2Sort, search } from './search.js';

const TEST_URL = 'https://dev.spinorama.org/index.html';
const METADATA_TEST_FILE = './tests/datas/metadata-20240516.json';

describe('urlParameters2Sort', () => {
    it('test search', () => {
        const url = new URL(TEST_URL + '?count=20&search=it');
        const params = urlParameters2Sort(url);
        const keywords = params[2];
        expect(params.length).toBe(4);
        expect(keywords).toBe('it');
        expect(params[3].count).toBe(20);
    });

    it('test sort', () => {
        const url = new URL(TEST_URL + '?sort=score');
        const params = urlParameters2Sort(url);
        const sorter = params[0];
        expect(sorter.by).toBe('score');
        expect(sorter.reverse).toBeFalsy();
    });

    it('test sort with reverse', () => {
        const url = new URL(TEST_URL + '?sort=score&reverse=true');
        const params = urlParameters2Sort(url);
        const sorter = params[0];
        expect(sorter.by).toBe('score');
        expect(sorter.reverse).toBeTruthy();
    });
});

describe('test full text search and filtering', () => {
    let metadata = null;

    beforeAll(() => {
        const bytes = readFileSync(METADATA_TEST_FILE, 'utf-8');
        const metajson = JSON.parse(bytes);
        metadata = new Map(Object.values(metajson).map((speaker) => [getID(speaker.brand, speaker.model), speaker]));
    });

    it('sanity check', () => {
        expect(metadata).toBeDefined();
        expect(metadata).toBeTypeOf('object');
        expect(metadata.size).toBeGreaterThan(100);
        expect(metadata.has('Genelec-8361A')).toBeTruthy();
        expect(metadata.has('Genelec 8361A')).toBeFalsy();
    });

    it('search basic genelec', () => {
        const url = new URL(TEST_URL + '?search=genelec&sort=score&page=1&count=15');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(15);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Genelec-8361A')).toBeTruthy();
        expect(results.includes('Genelec-8341A')).toBeTruthy();
        expect(results.includes('Genelec-8351B')).toBeTruthy();
    });

    it('search by brand revel', () => {
        const url = new URL(TEST_URL + '?brand=Revel&count=14');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(14);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Revel-F206')).toBeTruthy();
    });

    it('search by brand revel and active', () => {
        const url = new URL(TEST_URL + '?brand=Revel&count=14&power=active');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(0);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Revel-F206')).toBeFalsy();
    });

    it('search by brand revel and bookshelves', () => {
        const url = new URL(TEST_URL + '?brand=Revel&count=14&power=passive&shape=bookshelves');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(6);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Revel-F206')).toBeFalsy();
        expect(results.includes('Revel-M126Be')).toBeTruthy();
    });

    it('search by brand revel and bookshelves sorted by price', () => {
        const url = new URL(TEST_URL + '?brand=Revel&count=14&power=passive&shape=bookshelves&sort=price');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(6);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results[0]).toBe('Revel-M106');
        expect(results[1]).toBe('Revel-M126Be');
    });

    it('search by brand revel and bookshelves sorted by price, cheaper first', () => {
        const url = new URL(TEST_URL + '?brand=Revel&count=14&power=passive&shape=bookshelves&sort=price&reverse=true');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(6);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results[0]).toBe('Revel-Ultima2-Gem2');
        expect(results[1]).toBe('Revel-M16');
    });

    it('search by brand HK Audio and filter by weight', () => {
        const url = new URL(TEST_URL + '?brand=HK%20Audio&weightMin=20');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(7);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('HK-Audio-LINEAR-7-115-FA')).toBeTruthy();
    });

    it('search by brand HK Audio and filter by weight', () => {
        const url = new URL(TEST_URL + '?brand=HK%20Audio&weightMin=20');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.length).toBe(7);
        expect(results.includes('HK-Audio-LINEAR-7-115-FA')).toBeTruthy();
    });

    it('search by brand HK Audio and filter by weight', () => {
        const url = new URL(TEST_URL + '?brand=HK%20Audio&weightMin=20&weightMax=22');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(4);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('HK-Audio-LINEAR-7-115-FA')).toBeFalsy();
        expect(results.includes('HK-Audio-LINEAR-7-112-FA')).toBeTruthy();
    });

    it('search heavy weight', () => {
        const url = new URL(TEST_URL + '?weightMin=100');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(2);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('HK-Audio-LINEAR-7-112-FA')).toBeFalsy();
        expect(results.includes('EV-MTS-4153')).toBeTruthy();
    });

    it('search small width', () => {
        const url = new URL(TEST_URL + '?widthMax=170&count=100');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(22);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('HK-Audio-LINEAR-7-112-FA')).toBeFalsy();
        expect(results.includes('Acoustic-Energy-AE100-Mk2')).toBeTruthy();
    });

    it('search by price alone with Min and Max', () => {
        const priceMin = 100;
        const priceMax = 300;
        const href = TEST_URL + '?priceMin=' + priceMin + '&priceMax=' + priceMax + '&count=1000';
        const url = new URL(href);
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(maxResults).toBeDefined();
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(162);
        results.forEach((key) => {
            const result = metadata.get(key);
            let price = parseFloat(result.price);
            if (!result.amount || result?.amount === 'pair') {
                price /= 2.0;
            }
            expect(price).toBeGreaterThanOrEqual(priceMin);
            expect(price).toBeLessThanOrEqual(priceMax);
        });
    });

    it('search by price alone with Min and no Max', () => {
        const priceMin = 100;
        const href = TEST_URL + '?priceMin=' + priceMin + '&count=1000';
        const url = new URL(href);
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(maxResults).toBeDefined();
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(643);
        results.forEach((key) => {
            const result = metadata.get(key);
            let price = parseFloat(result.price);
            if (!result.amount || result?.amount === 'pair') {
                price /= 2.0;
            }
            expect(price).toBeGreaterThanOrEqual(priceMin);
        });
    });

    it('search by price alone with no Min and a Max', () => {
        const priceMax = 300;
        const href = TEST_URL + '?priceMax=' + priceMax + '&count=1000';
        const url = new URL(href);
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(maxResults).toBeDefined();
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(211);
        results.forEach((key) => {
            const result = metadata.get(key);
            let price = parseFloat(result.price);
            if (!result.amount || result?.amount === 'pair') {
                price /= 2.0;
            }
            expect(price).toBeLessThanOrEqual(priceMax);
        });
    });

    it('search by price : check that we have less results if the range is smaller', () => {
        function getResults(priceMax) {
            const href = TEST_URL + '?priceMax=' + priceMax + '&count=1000';
            const url = new URL(href);
            const params = urlParameters2Sort(url);
            return search(metadata, params);
        }
        const [maxResults1, results1] = getResults(100);
        const [maxResults2, results2] = getResults(200);
        expect(maxResults1).toBeLessThanOrEqual(maxResults2);
        expect(results1.length).toBeLessThanOrEqual(results2.length);
    });

    it('search by price : check that we have disjoint  results if the ranges do not intersect', () => {
        function getResults(priceMin, priceMax) {
            const href = TEST_URL + '?priceMin=' + priceMin + '&priceMax=' + priceMax + '&count=1000';
            const url = new URL(href);
            const params = urlParameters2Sort(url);
            return search(metadata, params);
        }
        const [maxResults1, results1] = getResults(100, 200);
        const [maxResults2, results2] = getResults(300, 1000);
        expect(maxResults1).toBeDefined();
        expect(maxResults2).toBeDefined();
        const set1 = new Set(results1);
        const set2 = new Set(results2);
        expect(set1.isDisjointFrom(set2)).toBeTruthy();
    });

    it('sort by price', () => {
        const href = TEST_URL + '?sort=price';
        const url = new URL(href);
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(maxResults).toBeDefined();
        expect(results[0]).toBe('KEF-Blade-1-Meta');
        expect(results[1]).toBe('JBL-Synthesis-SCL-1');
    });

    it('search no constraint page 1 & 2', () => {
        // page 1
        const url1 = new URL(TEST_URL + '?page=1&count=20');
        const params1 = urlParameters2Sort(url1);
        const [maxResults1, results1] = search(metadata, params1);
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        expect(maxResults1).toBeGreaterThanOrEqual(917);
        // page 2
        const url2 = new URL(TEST_URL + '?page=2&count=20');
        const params2 = urlParameters2Sort(url2);
        const [maxResults2, results2] = search(metadata, params2);
        expect(results2).toBeDefined();
        expect(results2).toBeTypeOf('object');
        expect(maxResults2).toBeGreaterThanOrEqual(917);
        // consistency
        expect(maxResults1).toEqual(maxResults2);
        const set1 = new Set(results1);
        const set2 = new Set(results2);
        // need node >22
        expect(set1.isDisjointFrom(set2)).toBeTruthy();
    });
});

describe('check within page', () => {
    it('test boundaries page 1 with 10 per page', () => {
        const pagination_1_10 = {
            active: true,
            page: 1,
            count: 10,
        };
        expect(isWithinPage(0, pagination_1_10)).toBeTruthy();
        expect(isWithinPage(1, pagination_1_10)).toBeTruthy();
        expect(isWithinPage(9, pagination_1_10)).toBeTruthy();
        expect(isWithinPage(10, pagination_1_10)).toBeFalsy();
    });

    it('test boundaries page 1 with 20 per page', () => {
        const pagination_1_20 = {
            active: true,
            page: 1,
            count: 20,
        };
        expect(isWithinPage(0, pagination_1_20)).toBeTruthy();
        expect(isWithinPage(1, pagination_1_20)).toBeTruthy();
        expect(isWithinPage(19, pagination_1_20)).toBeTruthy();
        expect(isWithinPage(20, pagination_1_20)).toBeFalsy();
    });

    it('test boundaries page 2 with 10 per page', () => {
        const pagination_2_10 = {
            active: true,
            page: 2,
            count: 10,
        };
        expect(isWithinPage(9, pagination_2_10)).toBeFalsy();
        expect(isWithinPage(10, pagination_2_10)).toBeTruthy();
        expect(isWithinPage(19, pagination_2_10)).toBeTruthy();
        expect(isWithinPage(20, pagination_2_10)).toBeFalsy();
    });
});

describe('non regression for bug discussions/279', () => {
    let metadata = null;
    let kef = null;
    let kef_by_date = null;

    function getDate(item) {
        const spk = item[1];
        let date = 19700101;
        // comparing ints (works because 20210101 is bigger than 20201010)
        for (const reviewer in spk.measurements) {
            const msr = spk.measurements[reviewer];
            if (msr?.review_published) {
                const reviewPublished = parseInt(msr.review_published);
                if (!isNaN(reviewPublished)) {
                    date = Math.max(reviewPublished, date);
                }
            }
        }
        return date;
    }

    beforeAll(() => {
        const bytes = readFileSync(METADATA_TEST_FILE, 'utf-8');
        const metajson = JSON.parse(bytes);
        metadata = new Map(Object.values(metajson).map((speaker) => [getID(speaker.brand, speaker.model), speaker]));
        kef = new Map(
            Object.values(metajson)
                .filter((speaker) => speaker.brand === 'KEF')
                .map((speaker) => [getID(speaker.brand, speaker.model), speaker])
        );

        kef_by_date = [...kef.entries()].sort((a, b) => {
            const da = getDate(a);
            const db = getDate(b);
            return db - da;
        });
    });

    it('search by brand KEF and check that we have the correct speakers', () => {
        const url = new URL(TEST_URL + '?brand=KEF');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(20);
        expect(maxResults).toBe(kef.size);
        expect(maxResults).toBe(35);
    });

    it('search by brand KEF and check that we have the correct speakers add page=1', () => {
        const url = new URL(TEST_URL + '?brand=KEF&page=1');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(20);
        expect(maxResults).toBe(kef.size);
        expect(maxResults).toBe(35);
    });

    it('search by brand KEF and sort by date', () => {
        const url = new URL(TEST_URL + '?brand=KEF&sort=date');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(maxResults).toBe(kef.size);
        expect(results[0]).toBe(kef_by_date[0][0]);
        expect(results[1]).toBe(kef_by_date[1][0]);
        expect(results[2]).toBe(kef_by_date[2][0]);
    });
});

describe('non regression for bug discussions/288', () => {
    let metadata = null;

    beforeAll(() => {
        const bytes = readFileSync(METADATA_TEST_FILE, 'utf-8');
        const metajson = JSON.parse(bytes);
        metadata = new Map(Object.values(metajson).map((speaker) => [getID(speaker.brand, speaker.model), speaker]));
    });

    it('search for JBL 306 and check that the results are sane', () => {
        const url1 = new URL(TEST_URL + '?search=JBL+306');
        const params1 = urlParameters2Sort(url1);
        const results1 = search(metadata, params1)[1];
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        expect(results1[0]).toBe('JBL-306P-Mark-ii');
    });

    it('search for JBL 306p and check that the results are sane', () => {
        const url1 = new URL(TEST_URL + '?search=JBL+306p');
        const params1 = urlParameters2Sort(url1);
        const results1 = search(metadata, params1)[1];
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        expect(results1[0]).toBe('JBL-306P-Mark-ii');
    });

    it('search for JBL 308p mark and check that the results are sane', () => {
        const url1 = new URL(TEST_URL + '?search=jbl+308+mark');
        const params1 = urlParameters2Sort(url1);
        const [maxResults1, results1] = search(metadata, params1);
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        expect(maxResults1).toBe(3);
        expect(results1[0]).toBe('JBL-308P-Mark-ii');
    });
});
