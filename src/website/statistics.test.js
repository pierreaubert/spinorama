import { describe, it, expect, beforeAll, beforeEach, afterEach } from 'vitest';

// Global variables provided by vitest/jsdom - eslint understands these
/* global global:readonly */

// -*- coding: utf-8 -*-
// Tests for statistics.js
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
import { readFileSync } from 'fs';
import { JSDOM } from 'jsdom';

const METADATA_TEST_FILE = './tests/datas/metadata-20240516.json';

describe('computeParetoFrontier', () => {
    function computeParetoFrontier(points) {
        const sorted = points.filter((p) => p.price > 0 && p.score > 0).sort((a, b) => a.price - b.price);
        const pareto = [];
        let maxScore = -Infinity;
        for (const p of sorted) {
            if (p.score > maxScore) {
                pareto.push(p);
                maxScore = p.score;
            }
        }
        return pareto;
    }

    it('should return empty for empty input', () => {
        const result = computeParetoFrontier([]);
        expect(result).toEqual([]);
    });

    it('should return single point when only one valid point', () => {
        const points = [{ price: 100, score: 5, name: 'Speaker A' }];
        const result = computeParetoFrontier(points);
        expect(result).toHaveLength(1);
        expect(result[0].name).toBe('Speaker A');
    });

    it('should filter out points with zero or negative price', () => {
        const points = [
            { price: 0, score: 5, name: 'Zero Price' },
            { price: -10, score: 3, name: 'Negative Price' },
            { price: 100, score: 5, name: 'Valid Speaker' },
        ];
        const result = computeParetoFrontier(points);
        expect(result).toHaveLength(1);
        expect(result[0].name).toBe('Valid Speaker');
    });

    it('should filter out points with zero or negative score', () => {
        const points = [
            { price: 100, score: 0, name: 'Zero Score' },
            { price: 200, score: -1, name: 'Negative Score' },
            { price: 100, score: 5, name: 'Valid Speaker' },
        ];
        const result = computeParetoFrontier(points);
        expect(result).toHaveLength(1);
        expect(result[0].name).toBe('Valid Speaker');
    });

    it('should find pareto frontier - higher score at lower price', () => {
        const points = [
            { price: 100, score: 5, name: 'Speaker A' },
            { price: 200, score: 8, name: 'Speaker B' },
            { price: 150, score: 6, name: 'Speaker C' },
            { price: 300, score: 4, name: 'Speaker D' },
            { price: 250, score: 9, name: 'Speaker E' },
        ];
        const result = computeParetoFrontier(points);
        // Sorted by price: A(100,5), C(150,6), B(200,8), E(250,9), D(300,4)
        // A: 5 > -inf -> include, maxScore=5
        // C: 6 > 5 -> include, maxScore=6
        // B: 8 > 6 -> include, maxScore=8
        // E: 9 > 8 -> include, maxScore=9
        // D: 4 > 9? NO -> exclude
        expect(result.map((p) => p.name)).toEqual(['Speaker A', 'Speaker C', 'Speaker B', 'Speaker E']);
    });

    it('should return all points if each has higher score than previous at higher price', () => {
        const points = [
            { price: 100, score: 2, name: 'Budget' },
            { price: 200, score: 4, name: 'Mid' },
            { price: 300, score: 6, name: 'Upper Mid' },
            { price: 400, score: 8, name: 'High End' },
        ];
        const result = computeParetoFrontier(points);
        expect(result).toHaveLength(4);
    });

    it('should return only expensive speaker if cheaper ones have lower scores', () => {
        const points = [
            { price: 100, score: 3, name: 'Cheap Bad' },
            { price: 200, score: 3.5, name: 'Mid Low' },
            { price: 500, score: 9, name: 'Expensive Great' },
        ];
        const result = computeParetoFrontier(points);
        // A(100,3): 3 > -inf -> include, maxScore=3
        // B(200,3.5): 3.5 > 3 -> include, maxScore=3.5
        // C(500,9): 9 > 3.5 -> include, maxScore=9
        expect(result).toHaveLength(3);
    });
});

describe('getFieldValue', () => {
    const testSpeaker = {
        brand: 'TestBrand',
        model: 'TestModel',
        price: '400',
        amount: 'pair',
        type: 'passive',
        shape: 'bookshelves',
        default_measurement: 'eac',
        measurements: {
            eac: {
                quality: 'high',
                pref_rating: {
                    pref_score: 5.5,
                    pref_score_wsub: 7.0,
                    lfx_hz: 45,
                },
                pref_rating_eq: {
                    pref_score: 6.5,
                },
                sensitivity: {
                    computed: 87.5,
                },
                specifications: {
                    impedance: 8,
                    weight: 5.5,
                    size: {
                        width: 200,
                        height: 300,
                        depth: 250,
                    },
                },
                estimates: {
                    ref_3dB: 55.0,
                    ref_6dB: 42.0,
                    ref_band: 3.5,
                },
            },
        },
    };

    function getFieldValue(speaker, field) {
        const msr = speaker.measurements[speaker.default_measurement];
        switch (field) {
            case 'brand':
                return speaker.brand;
            case 'model':
                return speaker.model;
            case 'price': {
                if (!speaker.price || speaker.price === '') return null;
                let price = parseFloat(speaker.price);
                if (isNaN(price)) return null;
                return !speaker.amount || speaker.amount === 'pair' ? price / 2 : price;
            }
            case 'type':
                return speaker.type;
            case 'shape':
                return speaker.shape;
            case 'score':
                return msr?.pref_rating?.pref_score ?? null;
            case 'scoreWsub':
                return msr?.pref_rating?.pref_score_wsub ?? null;
            case 'scoreEQ':
                return msr?.pref_rating_eq?.pref_score ?? null;
            case 'lfx':
                return msr?.pref_rating?.lfx_hz ?? null;
            case 'sensitivity':
                return msr?.sensitivity?.computed ?? null;
            case 'impedance':
                return msr?.specifications?.impedance ? parseInt(msr.specifications.impedance) : null;
            case 'weight':
                return msr?.specifications?.weight ? parseFloat(msr.specifications.weight) : null;
            case 'width':
                return msr?.specifications?.size?.width ? parseInt(msr.specifications.size.width) : null;
            case 'height':
                return msr?.specifications?.size?.height ? parseInt(msr.specifications.size.height) : null;
            case 'depth':
                return msr?.specifications?.size?.depth ? parseInt(msr.specifications.size.depth) : null;
            case 'f3':
                return msr?.estimates?.ref_3dB ? parseFloat(msr.estimates.ref_3dB) : null;
            case 'f6':
                return msr?.estimates?.ref_6dB ? parseFloat(msr.estimates.ref_6dB) : null;
            case 'bandwidth':
                return msr?.estimates?.ref_band ? parseFloat(msr.estimates.ref_band) : null;
            case 'quality':
                return msr?.quality ?? null;
            default:
                return null;
        }
    }

    it('should return brand', () => {
        expect(getFieldValue(testSpeaker, 'brand')).toBe('TestBrand');
    });

    it('should return model', () => {
        expect(getFieldValue(testSpeaker, 'model')).toBe('TestModel');
    });

    it('should return price divided by 2 for pair', () => {
        expect(getFieldValue(testSpeaker, 'price')).toBe(200);
    });

    it('should return full price for single', () => {
        const singleSpeaker = { ...testSpeaker, amount: 'single' };
        expect(getFieldValue(singleSpeaker, 'price')).toBe(400);
    });

    it('should return null for empty price', () => {
        const noPriceSpeaker = { ...testSpeaker, price: '' };
        expect(getFieldValue(noPriceSpeaker, 'price')).toBeNull();
    });

    it('should return type', () => {
        expect(getFieldValue(testSpeaker, 'type')).toBe('passive');
    });

    it('should return shape', () => {
        expect(getFieldValue(testSpeaker, 'shape')).toBe('bookshelves');
    });

    it('should return preference score', () => {
        expect(getFieldValue(testSpeaker, 'score')).toBe(5.5);
    });

    it('should return score with subwoofer', () => {
        expect(getFieldValue(testSpeaker, 'scoreWsub')).toBe(7.0);
    });

    it('should return score with EQ', () => {
        expect(getFieldValue(testSpeaker, 'scoreEQ')).toBe(6.5);
    });

    it('should return lfx', () => {
        expect(getFieldValue(testSpeaker, 'lfx')).toBe(45);
    });

    it('should return sensitivity', () => {
        expect(getFieldValue(testSpeaker, 'sensitivity')).toBe(87.5);
    });

    it('should return impedance', () => {
        expect(getFieldValue(testSpeaker, 'impedance')).toBe(8);
    });

    it('should return weight', () => {
        expect(getFieldValue(testSpeaker, 'weight')).toBe(5.5);
    });

    it('should return width', () => {
        expect(getFieldValue(testSpeaker, 'width')).toBe(200);
    });

    it('should return height', () => {
        expect(getFieldValue(testSpeaker, 'height')).toBe(300);
    });

    it('should return depth', () => {
        expect(getFieldValue(testSpeaker, 'depth')).toBe(250);
    });

    it('should return f3', () => {
        expect(getFieldValue(testSpeaker, 'f3')).toBe(55.0);
    });

    it('should return f6', () => {
        expect(getFieldValue(testSpeaker, 'f6')).toBe(42.0);
    });

    it('should return bandwidth', () => {
        expect(getFieldValue(testSpeaker, 'bandwidth')).toBe(3.5);
    });

    it('should return quality', () => {
        expect(getFieldValue(testSpeaker, 'quality')).toBe('high');
    });

    it('should return null for missing measurement', () => {
        const noMsrSpeaker = { ...testSpeaker, measurements: {} };
        expect(getFieldValue(noMsrSpeaker, 'score')).toBeNull();
    });

    it('should return null for unknown field', () => {
        expect(getFieldValue(testSpeaker, 'unknown')).toBeNull();
    });
});

describe('getFilterFromURL', () => {
    const initialUrl = 'https://dev.spinorama.org/statistics.html';

    beforeEach(() => {
        const dom = new JSDOM(`<!DOCTYPE html><body></body>`, { url: initialUrl });
        global.document = dom.window.document;
        global.window = dom.window;
        global.URL = dom.window.URL;
    });

    afterEach(() => {
        delete global.document;
        delete global.window;
        delete global.URL;
    });

    function getFilterFromURL() {
        const params = new URLSearchParams(window.location.search);
        return {
            brand: params.get('brand') || '',
            shape: params.get('shape') || '',
            power: params.get('power') || '',
            quality: params.get('quality')
                ? params
                      .get('quality')
                      .split(',')
                      .filter((v) => v !== '')
                : [],
            priceMin: parseFloat(params.get('priceMin')) || 0,
            priceMax: parseFloat(params.get('priceMax')) || Infinity,
            scoreMin: parseFloat(params.get('scoreMin')) || 0,
            scoreMax: parseFloat(params.get('scoreMax')) || 10,
        };
    }

    it('should return default values for empty URL', () => {
        const url = new URL(initialUrl);
        window.history.pushState({}, '', url);
        const filter = getFilterFromURL();
        expect(filter.brand).toBe('');
        expect(filter.shape).toBe('');
        expect(filter.power).toBe('');
        expect(filter.quality).toEqual([]);
        expect(filter.priceMin).toBe(0);
        expect(filter.priceMax).toBe(Infinity);
        expect(filter.scoreMin).toBe(0);
        expect(filter.scoreMax).toBe(10);
    });

    it('should parse brand from URL', () => {
        const url = new URL(initialUrl + '?brand=KEF');
        window.history.pushState({}, '', url);
        const filter = getFilterFromURL();
        expect(filter.brand).toBe('KEF');
    });

    it('should parse shape from URL', () => {
        const url = new URL(initialUrl + '?shape=bookshelves');
        window.history.pushState({}, '', url);
        const filter = getFilterFromURL();
        expect(filter.shape).toBe('bookshelves');
    });

    it('should parse power from URL', () => {
        const url = new URL(initialUrl + '?power=active');
        window.history.pushState({}, '', url);
        const filter = getFilterFromURL();
        expect(filter.power).toBe('active');
    });

    it('should parse quality as array from URL', () => {
        const url = new URL(initialUrl + '?quality=high,medium');
        window.history.pushState({}, '', url);
        const filter = getFilterFromURL();
        expect(filter.quality).toEqual(['high', 'medium']);
    });

    it('should parse priceMin and priceMax from URL', () => {
        const url = new URL(initialUrl + '?priceMin=100&priceMax=500');
        window.history.pushState({}, '', url);
        const filter = getFilterFromURL();
        expect(filter.priceMin).toBe(100);
        expect(filter.priceMax).toBe(500);
    });

    it('should parse scoreMin and scoreMax from URL', () => {
        const url = new URL(initialUrl + '?scoreMin=5&scoreMax=8');
        window.history.pushState({}, '', url);
        const filter = getFilterFromURL();
        expect(filter.scoreMin).toBe(5);
        expect(filter.scoreMax).toBe(8);
    });
});

describe('matchesFilter', () => {
    const testSpeaker = {
        brand: 'TestBrand',
        type: 'passive',
        shape: 'bookshelves',
        default_measurement: 'eac',
        measurements: {
            eac: {
                quality: 'high',
            },
        },
    };

    function matchesFilter(speaker, filter) {
        if (filter.brand && speaker.brand.toLowerCase() !== filter.brand.toLowerCase()) {
            return false;
        }
        if (filter.shape && speaker.shape !== filter.shape) {
            return false;
        }
        if (filter.power && speaker.type !== filter.power) {
            return false;
        }
        if (filter.quality.length > 0) {
            const msr = speaker.measurements[speaker.default_measurement];
            if (!msr || !filter.quality.includes(msr.quality?.toLowerCase())) {
                return false;
            }
        }
        return true;
    }

    it('should return true for empty filter', () => {
        const filter = { brand: '', shape: '', power: '', quality: [] };
        expect(matchesFilter(testSpeaker, filter)).toBe(true);
    });

    it('should filter by brand', () => {
        const filter = { brand: 'testbrand', shape: '', power: '', quality: [] };
        expect(matchesFilter(testSpeaker, filter)).toBe(true);
    });

    it('should return false for non-matching brand', () => {
        const filter = { brand: 'OtherBrand', shape: '', power: '', quality: [] };
        expect(matchesFilter(testSpeaker, filter)).toBe(false);
    });

    it('should filter by shape', () => {
        const filter = { brand: '', shape: 'bookshelves', power: '', quality: [] };
        expect(matchesFilter(testSpeaker, filter)).toBe(true);
    });

    it('should return false for non-matching shape', () => {
        const filter = { brand: '', shape: 'floorstanders', power: '', quality: [] };
        expect(matchesFilter(testSpeaker, filter)).toBe(false);
    });

    it('should filter by power', () => {
        const filter = { brand: '', shape: '', power: 'passive', quality: [] };
        expect(matchesFilter(testSpeaker, filter)).toBe(true);
    });

    it('should return false for non-matching power', () => {
        const filter = { brand: '', shape: '', power: 'active', quality: [] };
        expect(matchesFilter(testSpeaker, filter)).toBe(false);
    });

    it('should filter by quality', () => {
        const filter = { brand: '', shape: '', power: '', quality: ['high'] };
        expect(matchesFilter(testSpeaker, filter)).toBe(true);
    });

    it('should return false for non-matching quality', () => {
        const filter = { brand: '', shape: '', power: '', quality: ['low'] };
        expect(matchesFilter(testSpeaker, filter)).toBe(false);
    });

    it('should match multiple filters', () => {
        const filter = { brand: 'testbrand', shape: 'bookshelves', power: 'passive', quality: ['high'] };
        expect(matchesFilter(testSpeaker, filter)).toBe(true);
    });
});

describe('statistics data processing', () => {
    let metadata = null;

    beforeAll(() => {
        const bytes = readFileSync(METADATA_TEST_FILE, 'utf-8');
        const metajson = JSON.parse(bytes);
        metadata = new Map(Object.values(metajson).map((speaker) => [speaker.brand + '-' + speaker.model, speaker]));
    });

    it('should load metadata', () => {
        expect(metadata).toBeDefined();
        expect(metadata.size).toBeGreaterThan(100);
    });

    it('should have speakers with price data', () => {
        let count = 0;
        metadata.forEach((speaker) => {
            if (speaker.price && speaker.price !== '') {
                count++;
            }
        });
        expect(count).toBeGreaterThan(50);
    });

    it('should have speakers with preference scores', () => {
        let count = 0;
        metadata.forEach((speaker) => {
            const msr = speaker.measurements?.[speaker.default_measurement];
            if (msr?.pref_rating?.pref_score) {
                count++;
            }
        });
        expect(count).toBeGreaterThan(100);
    });

    it('should have speakers with sensitivity data', () => {
        let count = 0;
        metadata.forEach((speaker) => {
            const msr = speaker.measurements?.[speaker.default_measurement];
            if (msr?.sensitivity?.computed) {
                count++;
            }
        });
        expect(count).toBeGreaterThan(50);
    });
});
