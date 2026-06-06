// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-2026 Pierre Aubert pierre(at)spinorama(dot)org
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

/**
 * Client-side custom target curve handling for headphone pages.
 *
 * When a user uploads a custom target CSV (frequency,spl columns),
 * this module recomputes the deviation and updates the plotly graphs
 * in-place without a server round-trip.
 */

/**
 * Parse a CSV string with frequency,spl columns.
 * Skips comment lines (starting with #) and header lines.
 * @param {string} csvText
 * @returns {{freq: number[], spl: number[]}}
 */
export function parseTargetCSV(csvText) {
    const freq = [];
    const spl = [];
    const lines = csvText.split('\n');
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('f')) {
            continue;
        }
        const parts = trimmed.split(/[,\t]+/);
        if (parts.length >= 2) {
            const f = parseFloat(parts[0]);
            const s = parseFloat(parts[1]);
            if (!isNaN(f) && !isNaN(s)) {
                freq.push(f);
                spl.push(s);
            }
        }
    }
    return { freq, spl };
}

/**
 * Linear interpolation of target curve to measurement frequency grid.
 * @param {number[]} measFreq - measurement frequency points
 * @param {number[]} targetFreq - target frequency points
 * @param {number[]} targetSpl - target SPL values
 * @returns {number[]} interpolated target SPL at measurement frequencies
 */
export function interpolateTarget(measFreq, targetFreq, targetSpl) {
    const result = [];
    for (const f of measFreq) {
        if (f <= targetFreq[0]) {
            result.push(targetSpl[0]);
        } else if (f >= targetFreq[targetFreq.length - 1]) {
            result.push(targetSpl[targetSpl.length - 1]);
        } else {
            // Find bracketing indices
            let i = 0;
            while (i < targetFreq.length - 1 && targetFreq[i + 1] < f) {
                i++;
            }
            // Linear interpolation in log-frequency space
            const logF = Math.log10(f);
            const logF0 = Math.log10(targetFreq[i]);
            const logF1 = Math.log10(targetFreq[i + 1]);
            const t = (logF - logF0) / (logF1 - logF0);
            result.push(targetSpl[i] + t * (targetSpl[i + 1] - targetSpl[i]));
        }
    }
    return result;
}

/**
 * Set up the custom target curve upload handler.
 * Call this after the page has loaded.
 */
export function setupCustomTarget() {
    const selector = document.getElementById('selectTarget');
    const fileField = document.getElementById('customTargetField');
    const fileInput = document.getElementById('customTarget');

    if (!selector || !fileInput) {
        return;
    }

    selector.addEventListener('change', () => {
        if (selector.value === 'custom') {
            if (fileField) fileField.classList.remove('hidden');
        } else {
            if (fileField) fileField.classList.add('hidden');
        }
    });

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const csvText = e.target.result;
            const target = parseTargetCSV(csvText);
            if (target.freq.length < 2) {
                console.error('Custom target CSV must have at least 2 data points');
                return;
            }
            applyCustomTarget(target);
        };
        reader.readAsText(file);
    });
}

/**
 * Compute mean SPL inside [fmin, fmax] Hz.
 * @param {number[]} freq
 * @param {number[]} spl
 * @param {number} fmin
 * @param {number} fmax
 * @returns {number}
 */
function meanInBand(freq, spl, fmin, fmax) {
    let sum = 0;
    let count = 0;
    for (let i = 0; i < freq.length; i++) {
        if (freq[i] >= fmin && freq[i] <= fmax) {
            sum += spl[i];
            count++;
        }
    }
    return count > 0 ? sum / count : 0;
}

/**
 * Apply a custom target curve by updating the compensation and deviation graphs.
 * @param {{freq: number[], spl: number[]}} target
 */
function applyCustomTarget(target) {
    // Find the Frequency Response Compensated graph div
    const compDiv = document.querySelector('[id*="Frequency Response Compensated"]');
    const devDiv = document.querySelector('[id*="Target Deviation"]');

    if (!compDiv && !devDiv) {
        console.warn('No compensation or deviation graph found to update');
        return;
    }

    // Get the measurement data from the first trace of the compensated graph
    // The plotly data is stored in the div's data attribute after rendering
    if (compDiv && compDiv.data && compDiv.data.length > 0) {
        const measFreq = compDiv.data[0].x;
        const measSpl = compDiv.data[0].y;

        // Interpolate custom target to measurement grid
        const interpTarget = interpolateTarget(measFreq, target.freq, target.spl);

        // Normalize target over [300, 3000] Hz to match server-side graphs
        const meanTarget = meanInBand(measFreq, interpTarget, 300, 3000);
        const targetNorm = interpTarget.map((v) => v - meanTarget);

        // Update the target trace (second trace)
        if (compDiv.data.length > 1) {
            /* global Plotly */
            Plotly.restyle(compDiv, { y: [targetNorm] }, [1]);
            Plotly.relayout(compDiv, { 'data[1].name': 'Custom Target' });
        }

        // Update deviation graph
        if (devDiv && devDiv.data && devDiv.data.length > 0) {
            const deviation = measSpl.map((v, i) => v - targetNorm[i]);
            const meanDeviation = meanInBand(measFreq, deviation, 300, 3000);
            const deviationNorm = deviation.map((v) => v - meanDeviation);
            Plotly.restyle(devDiv, { y: [deviationNorm] }, [0]);
        }
    }
}
