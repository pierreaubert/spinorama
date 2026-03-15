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

const METADATA_TEST_FILE = './tests/datas/metadata-20240516.json';

// Reproduce the old buggy getNearSpeakers (only adds speakers with nearest to metaSpeakers)
function getNearSpeakersBuggy(metadata) {
    const metaSpeakers = {};
    const speakers = [];
    metadata.forEach(function (value) {
        const speaker = value.brand + ' ' + value.model;
        if (value.nearest && value.nearest.length > 0) {
            speakers.push(speaker);
            metaSpeakers[speaker] = value;
        }
    });
    return [metaSpeakers, speakers.sort()];
}

// Reproduce the fixed getNearSpeakers (adds all speakers to metaSpeakers)
function getNearSpeakersFixed(metadata) {
    const metaSpeakers = {};
    const speakers = [];
    metadata.forEach(function (value) {
        const speaker = value.brand + ' ' + value.model;
        metaSpeakers[speaker] = value;
        if (value.nearest && value.nearest.length > 0) {
            speakers.push(speaker);
        }
    });
    return [metaSpeakers, speakers.sort()];
}

describe('non regression: similar page neighbor lookup', () => {
    let metadata = null;

    beforeAll(() => {
        const bytes = readFileSync(METADATA_TEST_FILE, 'utf-8');
        const metajson = JSON.parse(bytes);
        metadata = new Map(Object.values(metajson).map((speaker) => [getID(speaker.brand, speaker.model), speaker]));
    });

    it('getNearSpeakers includes all speakers in metaSpeakers so neighbor lookups never fail', () => {
        const [metaSpeakers, speakers] = getNearSpeakersFixed(metadata);

        // speakers list should only contain speakers with nearest
        speakers.forEach((name) => {
            expect(metaSpeakers[name].nearest).toBeDefined();
            expect(metaSpeakers[name].nearest.length).toBeGreaterThan(0);
        });

        // every neighbor of every speaker must be in metaSpeakers
        for (const name of speakers) {
            const similars = metaSpeakers[name].nearest;
            for (const [, neighborName] of similars) {
                expect(metaSpeakers[neighborName]).toBeDefined();
                expect(metaSpeakers[neighborName].measurements).toBeDefined();
                expect(metaSpeakers[neighborName].default_measurement).toBeDefined();
            }
        }
    });

    it('getOrigin-style lookup on neighbor does not crash even when neighbor has no nearest data', () => {
        // Simulate the exact crash scenario: a speaker whose neighbor lacks nearest data.
        // Build a minimal metadata map with speakerA having nearest pointing to speakerB,
        // where speakerB has no nearest data.
        const speakerB = {
            brand: 'TestBrand',
            model: 'SpeakerB',
            default_measurement: 'asr',
            measurements: {
                asr: {
                    origin: 'ASR',
                    quality: 'high',
                    review_published: '20240101',
                },
            },
        };
        const speakerA = {
            brand: 'TestBrand',
            model: 'SpeakerA',
            default_measurement: 'asr',
            nearest: [[0.5, 'TestBrand SpeakerB']],
            measurements: {
                asr: {
                    origin: 'ASR',
                    quality: 'high',
                    review_published: '20240101',
                },
            },
        };

        const testMetadata = new Map([
            [getID('TestBrand', 'SpeakerA'), speakerA],
            [getID('TestBrand', 'SpeakerB'), speakerB],
        ]);

        // Fixed version: both speakers in metaSpeakers, only speakerA in dropdown
        const [metaFixed, speakersFixed] = getNearSpeakersFixed(testMetadata);
        expect(speakersFixed).toEqual(['TestBrand SpeakerA']);
        expect(metaFixed['TestBrand SpeakerB']).toBeDefined();
        expect(metaFixed['TestBrand SpeakerB'].measurements).toBeDefined();

        // Simulate what updatePlots does: look up neighbor in metaSpeakers
        const similars = metaFixed['TestBrand SpeakerA'].nearest;
        for (const [, neighborName] of similars) {
            const neighbor = metaFixed[neighborName];
            // This is what getOrigin does — it must not crash
            const measurements = Object.keys(neighbor.measurements);
            expect(measurements.length).toBeGreaterThan(0);
            const defaultMeasurement = neighbor.default_measurement;
            expect(neighbor.measurements[defaultMeasurement].origin).toBeDefined();
        }

        // Buggy version: speakerB missing from metaSpeakers
        const [metaBuggy, speakersBuggy] = getNearSpeakersBuggy(testMetadata);
        expect(speakersBuggy).toEqual(['TestBrand SpeakerA']);
        expect(metaBuggy['TestBrand SpeakerB']).toBeUndefined();
    });

    it('updatePlots skips neighbors that are not in metadata at all', () => {
        // Speaker with a neighbor that doesn't exist in any metadata
        const speakerC = {
            brand: 'TestBrand',
            model: 'SpeakerC',
            default_measurement: 'asr',
            nearest: [
                [0.3, 'TestBrand SpeakerD'],
                [0.7, 'NonExistent Speaker'],
                [0.9, 'TestBrand SpeakerD'],
            ],
            measurements: {
                asr: { origin: 'ASR', quality: 'high', review_published: '20240101' },
            },
        };
        const speakerD = {
            brand: 'TestBrand',
            model: 'SpeakerD',
            default_measurement: 'asr',
            measurements: {
                asr: { origin: 'ASR', quality: 'high', review_published: '20240101' },
            },
        };

        const testMetadata = new Map([
            [getID('TestBrand', 'SpeakerC'), speakerC],
            [getID('TestBrand', 'SpeakerD'), speakerD],
        ]);

        const [metaSpeakers] = getNearSpeakersFixed(testMetadata);

        // Simulate updatePlots: iterate neighbors, skip missing ones
        const similars = metaSpeakers['TestBrand SpeakerC'].nearest;
        const names = [];
        for (const [, neighborName] of similars) {
            if (!metaSpeakers[neighborName]) {
                continue;
            }
            names.push(neighborName);
            // getOrigin-style access must not crash
            const neighbor = metaSpeakers[neighborName];
            expect(neighbor.measurements).toBeDefined();
            expect(neighbor.measurements[neighbor.default_measurement].origin).toBeDefined();
        }
        // 'NonExistent Speaker' was skipped, 'TestBrand SpeakerD' added twice
        expect(names).toEqual(['TestBrand SpeakerD', 'TestBrand SpeakerD']);
    });
});
