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

import { describe, expect, it } from 'vitest';
import { computeDims } from './plot.js';

function graph_ratio(width, height) {
    width = Math.round(width);
    height = Math.round(height);
    let ratio = height / width;
    if (width > height) {
        ratio = width / height;
    }
    return ratio;
}

const screens = {
    // phones
    'iPhone SE': { width: 375, height: 667 },
    'iPhone 14 Pro Max': { width: 430, height: 932 },
    'Samsung Galaxy S8+': { width: 360, height: 740 },
    // tablets
    'iPad Pro': { width: 1024, height: 1366 },
    // desktops
    '16:9 2k': { width: 1920, height: 1080 },
    '16:9 4k': { width: 3840, height: 2160 },
};

/*
function swap(model) {
    return { width: model.height, height: model.width };
}
*/

describe('computeDims', () => {
    const ratioMin = 0.9;
    const ratioMax = 1.8;

    Object.entries(screens).forEach(([name, model]) => {
        it('testing ' + name + ' vertical compact 1', () => {
            const [width, height] = [...computeDims(model.width, model.height, true, true, 1)];

            const pWidth = width / model.width - 1.0;
            expect(pWidth).toBeCloseTo(0, 1);

            const ratio = graph_ratio(width, height);
            expect(ratio).toBeGreaterThan(ratioMin);
            expect(ratio).toBeLessThan(ratioMax);
        });
    });

    Object.entries(screens).forEach(([name, model]) => {
        it('testing ' + name + ' vertical compact 2', () => {
            const [width, height] = [...computeDims(model.width, model.height, true, true, 2)];

            const pWidth = width / model.width - 1.0;
            expect(pWidth).toBeCloseTo(0, 1);

            const ratio = graph_ratio(width, height);
            expect(ratio).toBeGreaterThan(ratioMin);
            expect(ratio).toBeLessThan(ratioMax);
        });
    });
});
