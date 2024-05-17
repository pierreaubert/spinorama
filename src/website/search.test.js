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

import { log } from 'console';
import { global, afterEach, beforeAll, beforeEach, describe, expect, test, it, vi } from 'vitest';
import { getID } from './misc.js';
import { urlParameters2Sort, search } from './search.js';

const fs = require('fs');

const METADATA_TEST_FILE = './tests/datas/metadata-20240516.json';

describe('urlParameters2Sort', () => {
    it('test search', () => {
        const url = new URL('https://spinorama.org/index.html?count=20&search=it');
        const params = urlParameters2Sort(url);
        const keywords = params[2];
        expect(params.length).toBe(4);
        expect(keywords).toBe('it');
        expect(params[3].count).toBe(20);
    });

    it('test sort', () => {
        const url = new URL('https://spinorama.org/index.html?sort=score');
        const params = urlParameters2Sort(url);
        const sorter = params[0];
        expect(sorter.by).toBe('score');
        expect(sorter.reverse).toBeFalsy();
    });

    it('test sort with reverse', () => {
        const url = new URL('https://spinorama.org/index.html?sort=score&reverse=true');
        const params = urlParameters2Sort(url);
        const sorter = params[0];
        expect(sorter.by).toBe('score');
        expect(sorter.reverse).toBeTruthy();
    });
});

describe('test search', () => {
    let metadata = null;

    beforeAll(() => {
        const bytes = fs.readFileSync(METADATA_TEST_FILE, 'utf-8');
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
        const url = new URL('https://spinorama.org/index.html?search=genelec&sort=score&page=1&count=15');
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
        const url = new URL('https://spinorama.org/index.html?brand=Revel&count=14');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(14);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Revel-F206')).toBeTruthy();
    });

    it('search by brand revel and active', () => {
        const url = new URL('https://spinorama.org/index.html?brand=Revel&count=14&power=active');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(0);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('Revel-F206')).toBeFalsy();
    });

    it('search by brand revel and bookshelves', () => {
        const url = new URL('https://spinorama.org/index.html?brand=Revel&count=14&power=passive&shape=bookshelves');
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
        const url = new URL('https://spinorama.org/index.html?brand=Revel&count=14&power=passive&shape=bookshelves&sort=price');
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
        const url = new URL(
            'https://spinorama.org/index.html?brand=Revel&count=14&power=passive&shape=bookshelves&sort=price&reverse=true'
        );
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
        const url = new URL('https://spinorama.org/index.html?brand=HK%20Audio&weightMin=20');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(7);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('HK-Audio-LINEAR-7-115-FA')).toBeTruthy();
    });

    it('search by brand HK Audio and filter by weight', () => {
        const url = new URL('https://spinorama.org/index.html?brand=HK%20Audio&weightMin=20');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.length).toBe(7);
        expect(results.includes('HK-Audio-LINEAR-7-115-FA')).toBeTruthy();
    });

    it('search by brand HK Audio and filter by weight', () => {
        const url = new URL('https://spinorama.org/index.html?brand=HK%20Audio&weightMin=20&weightMax=22');
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
        const url = new URL('https://spinorama.org/index.html?weightMin=100');
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
        const url = new URL('https://spinorama.org/index.html?widthMax=170&count=100');
        const params = urlParameters2Sort(url);
        const [maxResults, results] = search(metadata, params);
        expect(results).toBeDefined();
        expect(results).toBeTypeOf('object');
        expect(results.length).toBe(22);
        expect(maxResults).toBeGreaterThanOrEqual(results.length);
        expect(results.includes('HK-Audio-LINEAR-7-112-FA')).toBeFalsy();
        expect(results.includes('Acoustic-Energy-AE100-Mk2')).toBeTruthy();
    });
});
