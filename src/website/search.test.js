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
import { beforeAll, describe, expect, it, beforeEach, afterEach } from 'vitest'; // Added afterEach

import { getID } from './misc.js';
// Import 'process' and 'setupEventListener' and alias the original 'search' to avoid naming conflicts with the mock
import { isWithinPage, urlParameters2Sort, search as actualSearch } from './search.js';

import { JSDOM } from 'jsdom'; // For DOM manipulation in tests

const TEST_URL = 'https://dev.spinorama.org/index.html';
const METADATA_TEST_FILE = './tests/datas/metadata-20240516.json';

describe('urlParameters2Sort', () => {
    const initialUrl = TEST_URL;

    beforeEach(() => {
        // Setup JSDOM for tests in this suite
        const dom = new JSDOM(
            `
            <!DOCTYPE html>
            <html>
            <body>
                <input id="searchInput" />
                <select id="sortBy"><option value="date"></option><option value="score"></option></select>
                <input type="checkbox" id="sortReverse" />
            </body>
            </html>
        `,
            { url: initialUrl }
        );

        global.document = dom.window.document;
        global.window = dom.window;
        global.URL = dom.window.URL;
    });

    afterEach(() => {
        // Clean up JSDOM globals
        delete global.document;
        delete global.window;
        delete global.URL;
    });

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
    const initialUrl = TEST_URL; // Use the constant

    beforeAll(() => {
        const bytes = readFileSync(METADATA_TEST_FILE, 'utf-8');
        const metajson = JSON.parse(bytes);
        metadata = new Map(Object.values(metajson).map((speaker) => [getID(speaker.brand, speaker.model), speaker]));
    });

    beforeEach(() => {
        // Setup JSDOM for tests in this suite
        const dom = new JSDOM(
            `
            <!DOCTYPE html>
            <html>
            <body>
                <input id="searchInput" />
                <select id="sortBy"><option value="date"></option><option value="score"></option></select>
                <input type="checkbox" id="sortReverse" />
                <select id="selectReviewer"><option value=""></option><option value="erinsaudiocorner"></option></select>
                <label class="checkbox"><input type="checkbox" value="high" class="qualityCheckbox"> High</label>
                <label class="checkbox"><input type="checkbox" value="medium" class="qualityCheckbox"> Medium</label>
                <label class="checkbox"><input type="checkbox" value="low" class="qualityCheckbox"> Low</label>
                <label class="checkbox"><input type="checkbox" value="unknown" class="qualityCheckbox"> Unknown</label>
                <select id="selectShape"><option value="">All</option><option value="bookshelf">Bookshelf</option></select>
                <select id="selectPower"><option value="">All</option><option value="passive">Passive</option></select>
                <select id="selectBrand"><option value="">All</option><option value="KEF">KEF</option></select>
                <input id="inputPriceMin" />
                <input id="inputPriceMax" />
                <input id="inputWeightMin" />
                <input id="inputWeightMax" />
                <input id="inputHeightMin" />
                <input id="inputHeightMax" />
                <input id="inputWidthMin" />
                <input id="inputWidthMax" />
                <input id="inputDepthMin" />
                <input id="inputDepthMax" />
            </body>
            </html>
        `,
            { url: initialUrl }
        );

        global.document = dom.window.document;
        global.window = dom.window; // Required for URL processing within the functions
        global.URL = dom.window.URL; // Make sure URL constructor is from JSDOM
    });

    afterEach(() => {
        // Clean up JSDOM globals
        delete global.document;
        delete global.window;
        delete global.URL;
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
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(15);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Genelec-8361A')).toBeTruthy();
        expect(results.includes('Genelec-8341A')).toBeTruthy();
        expect(results.includes('Genelec-8351B')).toBeTruthy();
    });

    // Shapes for which the pref_score is shown on the speaker card.
    // Must match misc.js validShape — speakers with other shapes (inwall,
    // outdoor, surround, cbt, toursound, …) display *** instead of a score
    // and are sorted as score-less.
    const VALID_SHAPES = new Set(['floorstanders', 'bookshelves', 'center', 'columns', 'liveportable', 'cinema']);

    // Helper: extract pref_score for a speaker key (returns -10 if no displayed score)
    function getScore(key) {
        const spk = metadata.get(key);
        if (!spk) return -10;
        if (!VALID_SHAPES.has(spk.shape)) return -10;
        const def = spk.default_measurement;
        if (!def) return -10;
        const msr = spk.measurements?.[def];
        if (!msr?.pref_rating?.pref_score) return -10;
        return msr.pref_rating.pref_score;
    }

    it('search+sort: ?search=jbl&sort=score returns only JBL speakers sorted by score desc', () => {
        const url = new URL(TEST_URL + '?search=jbl&sort=score&page=1&count=20');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);

        // Must return some results
        expect(results.length).toBeGreaterThan(0);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);

        // Every returned speaker must be a JBL (search filter honored)
        for (const key of results) {
            const spk = metadata.get(key);
            expect(spk).toBeDefined();
            expect(spk.brand.toLowerCase()).toBe('jbl');
        }

        // Results must be sorted by score in descending order (sort param honored)
        for (let i = 1; i < results.length; i++) {
            const prev = getScore(results[i - 1]);
            const cur = getScore(results[i]);
            expect(prev).toBeGreaterThanOrEqual(cur);
        }

        // The top result should be the highest-scoring JBL in the metadata.
        // JBL-Control-HST-V2 has score 7.36 in the test fixture.
        expect(results[0]).toBe('JBL-Control-HST-V2');
    });

    it('search+sort: ?search=jbl&sort=score places no-score speakers LAST', () => {
        // Request enough results to include all 91 JBLs
        const url = new URL(TEST_URL + '?search=jbl&sort=score&page=1&count=200');
        const params = urlParameters2Sort(url);
        const [, results] = actualSearch(metadata, params);

        // There should be at least one no-score speaker in the fixture (JBL-LSR308)
        const scored = results.filter((k) => getScore(k) > -5);
        const noScore = results.filter((k) => getScore(k) <= -5);
        expect(noScore.length).toBeGreaterThan(0);

        // All scored speakers must appear BEFORE any no-score speaker.
        const lastScoredIdx = results.findLastIndex((k) => getScore(k) > -5);
        const firstNoScoreIdx = results.findIndex((k) => getScore(k) <= -5);
        expect(lastScoredIdx).toBeLessThan(firstNoScoreIdx);
    });

    it('search+sort: ?search=jbl&sort=score does not put inwall/cbt/outdoor speakers first', () => {
        // Regression: JBL-Control-24CT (shape: inwall) has pref_score=7.07 in
        // both the test fixture and the live data, but its score is hidden on
        // the card (***), so it must NOT be the top result. The top result
        // should be the highest-scoring JBL whose shape is in validShape.
        const url = new URL(TEST_URL + '?search=jbl&sort=score&page=1&count=20');
        const params = urlParameters2Sort(url);
        const [, results] = actualSearch(metadata, params);

        // Top result must be a "valid shape" JBL
        const top = metadata.get(results[0]);
        expect(top).toBeDefined();
        expect(VALID_SHAPES.has(top.shape)).toBe(true);

        // The known offender from live data must not be #1
        const idx24CT = results.indexOf('JBL-Control-24CT');
        expect(idx24CT).not.toBe(0);

        // And no inwall/outdoor/surround/cbt/toursound JBL should appear before
        // any "valid shape" JBL (they're all sentinel-scored).
        const lastValidIdx = results.findLastIndex((k) => {
            const s = metadata.get(k);
            return s && VALID_SHAPES.has(s.shape);
        });
        const firstInvalidIdx = results.findIndex((k) => {
            const s = metadata.get(k);
            return s && !VALID_SHAPES.has(s.shape);
        });
        if (firstInvalidIdx !== -1 && lastValidIdx !== -1) {
            expect(lastValidIdx).toBeLessThan(firstInvalidIdx);
        }
    });

    it('search+sort: robust against speakers with missing default_measurement', () => {
        // Create a hybrid metadata with one JBL missing default_measurement entirely
        const hybrid = new Map(metadata);
        hybrid.set('JBL-Fake-NoDefault', {
            brand: 'JBL',
            model: 'Fake NoDefault',
            type: 'passive',
            shape: 'bookshelves',
            // intentionally missing default_measurement
            measurements: {},
        });
        hybrid.set('JBL-Fake-NoRating', {
            brand: 'JBL',
            model: 'Fake NoRating',
            type: 'passive',
            shape: 'bookshelves',
            default_measurement: 'asr',
            measurements: {
                asr: {
                    // measurement object with no pref_rating
                    origin: 'ASR',
                },
            },
        });

        const url = new URL(TEST_URL + '?search=jbl&sort=score&page=1&count=200');
        const params = urlParameters2Sort(url);

        // This must not throw — getScore should tolerate missing fields
        let results;
        expect(() => {
            [, results] = actualSearch(hybrid, params);
        }).not.toThrow();

        // Both fake no-score speakers should be included, at the end
        expect(results).toContain('JBL-Fake-NoDefault');
        expect(results).toContain('JBL-Fake-NoRating');
        // The highest-scoring JBL must still be first
        expect(results[0]).toBe('JBL-Control-HST-V2');
    });

    it('search+sort: ?search=jbl&sort=price returns only JBL speakers sorted by price desc', () => {
        const url = new URL(TEST_URL + '?search=jbl&sort=price&page=1&count=30');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);

        expect(results.length).toBeGreaterThan(0);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);

        for (const key of results) {
            const spk = metadata.get(key);
            expect(spk.brand.toLowerCase()).toBe('jbl');
        }

        // Prices should be monotonically non-increasing
        function priceOf(key) {
            const spk = metadata.get(key);
            const p = parseFloat(spk?.price);
            if (isNaN(p)) return -1;
            return spk.amount === 'pair' ? p / 2 : p;
        }
        for (let i = 1; i < results.length; i++) {
            expect(priceOf(results[i - 1])).toBeGreaterThanOrEqual(priceOf(results[i]));
        }
    });

    it('search by brand revel', () => {
        const url = new URL(TEST_URL + '?brand=Revel&count=14');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(14);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Revel-F206')).toBeTruthy();
    });

    it('search by brand revel and active', () => {
        const url = new URL(TEST_URL + '?brand=Revel&count=14&power=active');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(0);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Revel-F206')).toBeFalsy();
    });

    it('search by brand revel and bookshelves', () => {
        const url = new URL(TEST_URL + '?brand=Revel&count=14&power=passive&shape=bookshelves');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
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
        const [maxResults, results] = actualSearch(metadata, params);
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
        const [maxResults, results] = actualSearch(metadata, params);
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
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(7);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('HK-Audio-LINEAR-7-115-FA')).toBeTruthy();
    });

    it('search by brand HK Audio and filter by weight', () => {
        const url = new URL(TEST_URL + '?brand=HK%20Audio&weightMin=20');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.length).toBe(7);
        expect(results.includes('HK-Audio-LINEAR-7-115-FA')).toBeTruthy();
    });

    it('search by brand HK Audio and filter by weight', () => {
        const url = new URL(TEST_URL + '?brand=HK%20Audio&weightMin=20&weightMax=22');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
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
        const [maxResults, results] = actualSearch(metadata, params);
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
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(22);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('HK-Audio-LINEAR-7-112-FA')).toBeFalsy();
        expect(results.includes('Acoustic-Energy-AE100-Mk2')).toBeTruthy();
    });

    it('filter by f3 min', () => {
        const url = new URL(TEST_URL + '?f3Min=50&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(725);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Acoustic-Energy-AE100-Mk2')).toBeTruthy();
    });

    it('filter by f3 max', () => {
        const url = new URL(TEST_URL + '?f3Max=50&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(167);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Acoustic-Energy-AE100-Mk2')).toBeFalsy();
    });

    it('filter by f3 min and max', () => {
        const url = new URL(TEST_URL + '?f3Min=40&f3Max=80&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(555);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        results.forEach((key) => {
            const result = metadata.get(key);
            const msr = result.measurements[result.default_measurement];
            const f3 = msr.estimates.ref_3dB;
            expect(f3).toBeGreaterThanOrEqual(40);
            expect(f3).toBeLessThanOrEqual(80);
        });
    });

    it('filter by f6 min', () => {
        const url = new URL(TEST_URL + '?f6Min=40&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(761);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Acoustic-Energy-AE100-Mk2')).toBeTruthy();
    });

    it('filter by f6 max', () => {
        const url = new URL(TEST_URL + '?f6Max=40&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(135);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Acoustic-Energy-AE100-Mk2')).toBeFalsy();
    });

    it('filter by f6 min and max', () => {
        const url = new URL(TEST_URL + '?f6Min=30&f6Max=60&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(481);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        results.forEach((key) => {
            const result = metadata.get(key);
            const msr = result.measurements[result.default_measurement];
            const f6 = msr.estimates.ref_6dB;
            expect(f6).toBeGreaterThanOrEqual(30);
            expect(f6).toBeLessThanOrEqual(60);
        });
    });

    it('filter by f3 and f6 combined', () => {
        const url = new URL(TEST_URL + '?f3Min=40&f3Max=70&f6Min=30&f6Max=50&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(243);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        results.forEach((key) => {
            const result = metadata.get(key);
            const msr = result.measurements[result.default_measurement];
            const f3 = msr.estimates.ref_3dB;
            const f6 = msr.estimates.ref_6dB;
            expect(f3).toBeGreaterThanOrEqual(40);
            expect(f3).toBeLessThanOrEqual(70);
            expect(f6).toBeGreaterThanOrEqual(30);
            expect(f6).toBeLessThanOrEqual(50);
        });
    });

    it('filter by sensitivity min', () => {
        const url = new URL(TEST_URL + '?sensitivityMin=85&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(422);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by sensitivity max', () => {
        const url = new URL(TEST_URL + '?sensitivityMax=85&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(209);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by sensitivity min and max', () => {
        const url = new URL(TEST_URL + '?sensitivityMin=80&sensitivityMax=90&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(433);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        results.forEach((key) => {
            const result = metadata.get(key);
            const msr = result.measurements[result.default_measurement];
            const sensitivity = msr.sensitivity.computed;
            expect(sensitivity).toBeGreaterThanOrEqual(80);
            expect(sensitivity).toBeLessThanOrEqual(90);
        });
    });

    it('filter by impedance min', () => {
        const url = new URL(TEST_URL + '?impedanceMin=8&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(64);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by impedance max', () => {
        const url = new URL(TEST_URL + '?impedanceMax=8&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(132);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by lfx min', () => {
        const url = new URL(TEST_URL + '?lfxMin=40&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(757);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by lfx max', () => {
        const url = new URL(TEST_URL + '?lfxMax=40&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(163);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by lfx min and max', () => {
        const url = new URL(TEST_URL + '?lfxMin=30&lfxMax=50&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(313);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        results.forEach((key) => {
            const result = metadata.get(key);
            const msr = result.measurements[result.default_measurement];
            const lfx = msr.pref_rating.lfx_hz;
            expect(lfx).toBeGreaterThanOrEqual(30);
            expect(lfx).toBeLessThanOrEqual(50);
        });
    });

    it('filter by spl min', () => {
        const url = new URL(TEST_URL + '?splMin=110&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(132);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by spl max', () => {
        const url = new URL(TEST_URL + '?splMax=110&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(19);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by bandwidth min', () => {
        const url = new URL(TEST_URL + '?bandwidthMin=3&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(475);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by bandwidth max', () => {
        const url = new URL(TEST_URL + '?bandwidthMax=3&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(468);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
    });

    it('filter by bandwidth min and max', () => {
        const url = new URL(TEST_URL + '?bandwidthMin=2&bandwidthMax=4&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(522);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        results.forEach((key) => {
            const result = metadata.get(key);
            const msr = result.measurements[result.default_measurement];
            const bandwidth = msr.estimates.ref_band;
            expect(bandwidth).toBeGreaterThanOrEqual(2);
            expect(bandwidth).toBeLessThanOrEqual(4);
        });
    });

    it('search by price alone with Min and Max', () => {
        const priceMin = 100;
        const priceMax = 300;
        const href = TEST_URL + '?priceMin=' + priceMin + '&priceMax=' + priceMax + '&count=1000';
        const url = new URL(href);
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
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
        const [maxResults, results] = actualSearch(metadata, params);
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
        const [maxResults, results] = actualSearch(metadata, params);
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
            return actualSearch(metadata, params);
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
            return actualSearch(metadata, params);
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
        const [maxResults, results] = actualSearch(metadata, params);
        expect(maxResults).toBeDefined();
        expect(results[0]).toBe('KEF-Blade-1-Meta');
        expect(results[1]).toBe('JBL-Synthesis-SCL-1');
    });

    it('filter by single quality high', () => {
        const url = new URL(TEST_URL + '?quality=high&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(maxResults).toBeGreaterThan(0);
        results.forEach((key) => {
            const speaker = metadata.get(key);
            const qualities = Object.values(speaker.measurements).map((m) => m.quality.toLowerCase());
            expect(qualities.some((q) => q === 'high')).toBeTruthy();
        });
    });

    it('filter by multiple qualities high,medium', () => {
        const url = new URL(TEST_URL + '?quality=high,medium&count=1000');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(maxResults).toBeGreaterThan(0);
        results.forEach((key) => {
            const speaker = metadata.get(key);
            const qualities = Object.values(speaker.measurements).map((m) => m.quality.toLowerCase());
            expect(qualities.some((q) => q === 'high' || q === 'medium')).toBeTruthy();
        });
    });

    it('filter by multiple qualities returns more results than single quality', () => {
        const urlSingle = new URL(TEST_URL + '?quality=high&count=1000');
        const paramsSingle = urlParameters2Sort(urlSingle);
        const [maxSingle] = actualSearch(metadata, paramsSingle);

        const urlMulti = new URL(TEST_URL + '?quality=high,medium&count=1000');
        const paramsMulti = urlParameters2Sort(urlMulti);
        const [maxMulti] = actualSearch(metadata, paramsMulti);

        expect(maxMulti).toBeGreaterThanOrEqual(maxSingle);
    });

    it('empty quality filter returns all speakers', () => {
        const urlNoFilter = new URL(TEST_URL + '?count=1000');
        const paramsNoFilter = urlParameters2Sort(urlNoFilter);
        const [maxNoFilter] = actualSearch(metadata, paramsNoFilter);

        expect(maxNoFilter).toBeGreaterThan(0);
    });

    it('search no constraint page 1 & 2', () => {
        // page 1
        const url1 = new URL(TEST_URL + '?page=1&count=20');
        const params1 = urlParameters2Sort(url1);
        const [maxResults1, results1] = actualSearch(metadata, params1);
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        expect(maxResults1).toBeGreaterThanOrEqual(917);
        // page 2
        const url2 = new URL(TEST_URL + '?page=2&count=20');
        const params2 = urlParameters2Sort(url2);
        const [maxResults2, results2] = actualSearch(metadata, params2);
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
    const initialUrl = TEST_URL; // Added for JSDOM

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

    beforeEach(() => {
        // Setup JSDOM for tests in this suite
        const dom = new JSDOM(
            `
            <!DOCTYPE html>
            <html>
            <body>
                <input id="searchInput" />
                <select id="sortBy"><option value="date"></option><option value="score"></option></select>
                <input type="checkbox" id="sortReverse" />
                <select id="selectBrand"><option value="">All</option><option value="KEF">KEF</option></select>
                <!-- Simplified DOM for these specific tests; expand if more selectors are used by urlParameters2Sort -->
            </body>
            </html>
        `,
            { url: initialUrl }
        );

        global.document = dom.window.document;
        global.window = dom.window;
        global.URL = dom.window.URL;
    });

    afterEach(() => {
        // Clean up JSDOM globals
        delete global.document;
        delete global.window;
        delete global.URL;
    });

    it('search by brand KEF and check that we have the correct speakers', () => {
        const url = new URL(TEST_URL + '?brand=KEF');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(20);
        expect(maxResults).toBe(kef.size);
        expect(maxResults).toBe(35);
    });

    it('search by brand KEF and check that we have the correct speakers add page=1', () => {
        const url = new URL(TEST_URL + '?brand=KEF&page=1');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(20);
        expect(maxResults).toBe(kef.size);
        expect(maxResults).toBe(35);
    });

    it('search by brand KEF and sort by date', () => {
        const url = new URL(TEST_URL + '?brand=KEF&sort=date');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = actualSearch(metadata, params);
        expect(maxResults).toBe(kef.size);
        expect(results[0]).toBe(kef_by_date[0][0]);
        expect(results[1]).toBe(kef_by_date[1][0]);
        expect(results[2]).toBe(kef_by_date[2][0]);
    });
});

describe('non regression for bug discussions/288', () => {
    let metadata = null;
    const initialUrl = TEST_URL; // Added for JSDOM

    beforeAll(() => {
        const bytes = readFileSync(METADATA_TEST_FILE, 'utf-8');
        const metajson = JSON.parse(bytes);
        metadata = new Map(Object.values(metajson).map((speaker) => [getID(speaker.brand, speaker.model), speaker]));
    });

    beforeEach(() => {
        // Setup JSDOM for tests in this suite
        const dom = new JSDOM(
            `
            <!DOCTYPE html>
            <html>
            <body>
                <input id="searchInput" />
                <select id="sortBy"><option value="date"></option><option value="score"></option></select>
                <input type="checkbox" id="sortReverse" />
                <!-- Simplified DOM; expand if more selectors are used -->
            </body>
            </html>
        `,
            { url: initialUrl }
        );

        global.document = dom.window.document;
        global.window = dom.window;
        global.URL = dom.window.URL;
    });

    afterEach(() => {
        // Clean up JSDOM globals
        delete global.document;
        delete global.window;
        delete global.URL;
    });

    it('search for JBL 306 and check that the results are sane', () => {
        const url1 = new URL(TEST_URL + '?search=JBL+306');
        const params1 = urlParameters2Sort(url1);
        const results1 = actualSearch(metadata, params1)[1];
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        expect(results1[0]).toBe('JBL-306P-Mark-ii');
    });

    it('search for JBL 306p and check that the results are sane', () => {
        const url1 = new URL(TEST_URL + '?search=JBL+306p');
        const params1 = urlParameters2Sort(url1);
        const results1 = actualSearch(metadata, params1)[1];
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        expect(results1[0]).toBe('JBL-306P-Mark-ii');
    });

    it('search for JBL 308p mark and check that the results are sane', () => {
        const url1 = new URL(TEST_URL + '?search=jbl+308+mark');
        const params1 = urlParameters2Sort(url1);
        const [maxResults1, results1] = actualSearch(metadata, params1);
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        expect(maxResults1).toBe(3);
        expect(results1[0]).toBe('JBL-308P-Mark-ii');
    });
});

describe('non regression for bug discussions/343', () => {
    let metadata = null;
    const initialUrl = TEST_URL; // Added for JSDOM

    beforeAll(() => {
        const bytes = readFileSync(METADATA_TEST_FILE, 'utf-8');
        const metajson = JSON.parse(bytes);
        metadata = new Map(Object.values(metajson).map((speaker) => [getID(speaker.brand, speaker.model), speaker]));
    });

    beforeEach(() => {
        // Setup JSDOM for tests in this suite
        const dom = new JSDOM(
            `
            <!DOCTYPE html>
            <html>
            <body>
                <input id="searchInput" />
                <select id="sortBy"><option value="date"></option><option value="score"></option></select>
                <input type="checkbox" id="sortReverse" />
                <!-- Simplified DOM; expand if more selectors are used -->
            </body>
            </html>
        `,
            { url: initialUrl }
        );

        global.document = dom.window.document;
        global.window = dom.window;
        global.URL = dom.window.URL;
    });

    afterEach(() => {
        // Clean up JSDOM globals
        delete global.document;
        delete global.window;
        delete global.URL;
    });

    it('search for KEF R3 and check that the results are sane', () => {
        const url1 = new URL(TEST_URL + '?search=R3');
        const params1 = urlParameters2Sort(url1);
        const [maxResults1, results1] = actualSearch(metadata, params1);
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        // Only the two exact-match KEF R3 variants should be returned
        // (previously the test asserted 31, but that was the broken behavior
        // where partial matches leaked through due to a Map.length/.size bug).
        expect(maxResults1).toBe(2);
        expect(results1).toContain('KEF-R3');
        expect(results1).toContain('KEF-R3-Meta');
    });

    it('search for 4C Meta and check that the results are sane', () => {
        const url1 = new URL(TEST_URL + '?search=4C+Meta');
        const params1 = urlParameters2Sort(url1);
        const [maxResults1, results1] = actualSearch(metadata, params1);
        expect(results1).toBeDefined();
        expect(results1).toBeTypeOf('object');
        expect(maxResults1).toBe(1);
        expect(results1[0]).toBe('KEF-Reference-4C-Meta');
    });
});
