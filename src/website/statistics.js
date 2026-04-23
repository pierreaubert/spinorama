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

/*global Plotly*/
/*eslint no-undef: "error"*/

import { getMetadata } from './download.js';

getMetadata()
    .then((metadata) => {
        function plotScoreDistribution(scores, scoresEQ) {
            const traceScores = {
                x: scores,
                type: 'histogram',
                opacity: 0.5,
                marker: {
                    color: 'blue',
                },
                name: 'Score',
            };
            const traceScoresEQ = {
                x: scoresEQ,
                type: 'histogram',
                opacity: 0.5,
                marker: {
                    color: 'orange',
                },
                name: 'Score w/EQ',
            };
            const data = [traceScores, traceScoresEQ];
            const layout = {
                autosize: true,
                height: 280,
                title: { text: 'Distribution of scores' },
                xaxis: {
                    title: 'Score',
                    range: [0, 10],
                },
                yaxis: { title: 'Count', nticks: 5 },
                barmode: 'overlay',
                legend: {
                    orientation: 'h',
                    y: -0.2,
                },
                margin: { l: 50, r: 20, t: 40, b: 40 },
            };
            Plotly.newPlot('visScoreDistribution', data, layout, { responsive: true });
        }

        function plotScoreDistributionWsub(scores, scoresEQ) {
            const traceScores = {
                x: scores,
                type: 'histogram',
                opacity: 0.5,
                marker: {
                    color: 'blue',
                },
                name: 'Score w/Sub',
            };
            const traceScoresEQ = {
                x: scoresEQ,
                type: 'histogram',
                opacity: 0.5,
                marker: {
                    color: 'orange',
                },
                name: 'Score w/Sub+w/EQ',
            };
            const data = [traceScores, traceScoresEQ];
            const layout = {
                autosize: true,
                height: 280,
                title: { text: 'Distribution of scores with a perfect subwoofer' },
                xaxis: {
                    title: 'Score',
                    range: [0, 10],
                },
                yaxis: {
                    title: 'Count',
                    nticks: 5,
                },
                barmode: 'overlay',
                legend: {
                    orientation: 'h',
                    y: -0.2,
                },
                margin: { l: 50, r: 20, t: 40, b: 40 },
            };
            Plotly.newPlot('visScoreDistributionWsub', data, layout, { responsive: true });
        }

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

        function computeLinearRegression(xValues, yValues, options = {}) {
            const { logX = false, logY = false } = options;
            const n = xValues.length;
            if (n < 2) return null;

            const validPairs = [];
            for (let i = 0; i < n; i++) {
                const x = logX ? (xValues[i] > 0 ? Math.log10(xValues[i]) : NaN) : xValues[i];
                const y = logY ? (yValues[i] > 0 ? Math.log10(yValues[i]) : NaN) : yValues[i];
                if (!isNaN(x) && !isNaN(y)) {
                    validPairs.push({ x, y, origX: xValues[i] });
                }
            }

            if (validPairs.length < 2) return null;

            const validX = validPairs.map((p) => p.x);
            const validY = validPairs.map((p) => p.y);
            const origXValues = validPairs.map((p) => p.origX);

            const sumX = validX.reduce((a, b) => a + b, 0);
            const sumY = validY.reduce((a, b) => a + b, 0);
            const sumXY = validX.reduce((acc, x, i) => acc + x * validY[i], 0);
            const sumX2 = validX.reduce((acc, x) => acc + x * x, 0);

            const slope = (validX.length * sumXY - sumX * sumY) / (validX.length * sumX2 - sumX * sumX);
            const intercept = (sumY - slope * sumX) / validX.length;

            const minX = Math.min(...origXValues);
            const maxX = Math.max(...origXValues);

            let yMin, yMax;
            if (logX) {
                yMin = Math.pow(10, slope * Math.log10(minX) + intercept);
                yMax = Math.pow(10, slope * Math.log10(maxX) + intercept);
            } else {
                yMin = slope * minX + intercept;
                yMax = slope * maxX + intercept;
            }

            if (logY) {
                yMin = Math.pow(10, yMin);
                yMax = Math.pow(10, yMax);
            }

            return {
                slope,
                intercept,
                x: [minX, maxX],
                y: [yMin, yMax],
            };
        }

        function computeParetoCurveForData(xValues, yValues, options = {}) {
            const { direction = 'max' } = options;
            const points = xValues.map((x, i) => ({ x, y: yValues[i] }));
            const sorted = points
                .filter((p) => p.x !== null && p.y !== null && !isNaN(p.x) && !isNaN(p.y))
                .sort((a, b) => a.x - b.x);

            const pareto = [];
            if (direction === 'max') {
                let maxY = -Infinity;
                for (const p of sorted) {
                    if (p.y > maxY) {
                        pareto.push(p);
                        maxY = p.y;
                    }
                }
            } else {
                let minY = Infinity;
                for (const p of sorted) {
                    if (p.y < minY) {
                        pareto.push(p);
                        minY = p.y;
                    }
                }
            }
            return {
                x: pareto.map((p) => p.x),
                y: pareto.map((p) => p.y),
            };
        }

        function plotValueChart(prices, scores, names, divname) {
            const points = prices.map((p, i) => ({ price: p, score: scores[i], name: names[i] }));
            const pareto = computeParetoFrontier(points);
            const paretoSet = new Set(pareto.map((p) => p.name));

            const nonPareto = {
                x: points.filter((p) => !paretoSet.has(p.name)).map((p) => p.price),
                y: points.filter((p) => !paretoSet.has(p.name)).map((p) => p.score),
                mode: 'markers',
                type: 'scatter',
                name: 'Other speakers',
                text: points.filter((p) => !paretoSet.has(p.name)).map((p) => p.name),
                marker: {
                    size: 8,
                    color: 'rgba(100, 100, 100, 0.5)',
                },
            };

            const paretoTrace = {
                x: pareto.map((p) => p.price),
                y: pareto.map((p) => p.score),
                mode: 'markers',
                type: 'scatter',
                name: 'Best Value (Pareto)',
                text: pareto.map((p) => p.name),
                marker: {
                    size: 12,
                    color: 'red',
                    line: {
                        color: 'darkred',
                        width: 2,
                    },
                },
            };

            const paretoLine = {
                x: pareto.map((p) => p.price),
                y: pareto.map((p) => p.score),
                mode: 'lines',
                type: 'scatter',
                name: 'Pareto Frontier',
                line: {
                    color: 'red',
                    width: 2,
                    dash: 'dash',
                },
                hoverinfo: 'skip',
            };

            const data = [nonPareto, paretoTrace, paretoLine];
            const layout = {
                autosize: true,
                title: { text: 'Value Chart: Price vs Preference Score' },
                xaxis: {
                    title: 'Price (USD, each)',
                    type: 'log',
                },
                yaxis: {
                    title: 'Preference Score',
                    range: [0, 10],
                },
                legend: {
                    orientation: 'h',
                    y: -0.2,
                },
                hovermode: 'closest',
                margin: { l: 50, r: 20, t: 40, b: 40 },
            };
            Plotly.newPlot(divname, data, layout, { responsive: true });
        }

        function plotParameters(name, title, param, scores, names, divname) {
            const trace = {
                x: scores,
                y: param,
                mode: 'markers',
                type: 'scatter',
                name: name,
                text: names,
            };
            const data = [trace];
            const layout = {
                autosize: true,
                title: { text: title },
                legend: {
                    orientation: 'h',
                    y: -0.2,
                },
                xaxis: {
                    title: 'Score',
                },
                yaxis: {
                    title: name,
                },
                margin: { l: 50, r: 20, t: 40, b: 40 },
            };
            Plotly.newPlot(divname, data, layout, { responsive: true });
        }

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

        function stats() {
            const filter = getFilterFromURL();
            const scores = [];
            const scoresEQ = [];
            const scoresWsub = [];
            const scoresWsubEQ = [];
            const lfx = [];
            const nbdON = [];
            const nbdPIR = [];
            const smPIR = [];
            const names = [];
            const prices = [];
            const scoresForPrice = [];
            metadata.forEach((value) => {
                if (!matchesFilter(value, filter)) {
                    return;
                }
                if (
                    value.measurements &&
                    value.measurements[value.default_measurement] &&
                    value.measurements[value.default_measurement].pref_rating &&
                    value.measurements[value.default_measurement].pref_rating.pref_score
                ) {
                    // gather various scores
                    scores.push(value.measurements[value.default_measurement].pref_rating.pref_score);
                    scoresWsub.push(value.measurements[value.default_measurement].pref_rating.pref_score_wsub);
                    // components of the score
                    lfx.push(value.measurements[value.default_measurement].pref_rating.lfx_hz);
                    nbdON.push(value.measurements[value.default_measurement].pref_rating.nbd_on_axis);
                    nbdPIR.push(value.measurements[value.default_measurement].pref_rating.nbd_pred_in_room);
                    smPIR.push(value.measurements[value.default_measurement].pref_rating.sm_pred_in_room);
                    // price (each speaker, not pair)
                    let price = 0;
                    let hasPrice = false;
                    if (value.price && value.price !== '') {
                        const parsedPrice = parseFloat(value.price);
                        if (!isNaN(parsedPrice) && parsedPrice > 0) {
                            price = parsedPrice;
                            if (!value.amount || value.amount === 'pair') {
                                price /= 2.0;
                            }
                            hasPrice = true;
                        }
                    }
                    const score = value.measurements[value.default_measurement].pref_rating.pref_score;
                    if (
                        hasPrice &&
                        price >= filter.priceMin &&
                        price <= filter.priceMax &&
                        score >= filter.scoreMin &&
                        score <= filter.scoreMax
                    ) {
                        prices.push(price);
                        names.push(value.brand + ' ' + value.model);
                        scoresForPrice.push(score);
                    }
                }
                if (
                    value.measurements &&
                    value.measurements[value.default_measurement] &&
                    value.measurements[value.default_measurement].pref_rating_eq &&
                    value.measurements[value.default_measurement].pref_rating_eq.pref_score
                ) {
                    // gather various scores
                    scoresEQ.push(value.measurements[value.default_measurement].pref_rating_eq.pref_score);
                    scoresWsubEQ.push(value.measurements[value.default_measurement].pref_rating_eq.pref_score_wsub);
                }
            });
            // console.log('found ' + scores.length + ' scores')
            plotScoreDistribution(scores, scoresEQ);
            plotScoreDistributionWsub(scoresWsub, scoresWsubEQ);
            plotValueChart(prices, scoresForPrice, names, 'visValueChart');
            plotParameters('LFX (Hz)', 'Low Frequency eXtension (LFX) v.s. Score', lfx, scores, names, 'visDistributionLfxHz');
            plotParameters(
                'NBD ON',
                'Narrow Bandwidth On Axis (NBD ON) v.s. Score',
                nbdON,
                scores,
                names,
                'visDistributionNbdOn'
            );
            plotParameters(
                'NBD PIR',
                'Narrow Bandwidth Predicted In Room (NBD PIR) v.s. Score',
                nbdPIR,
                scores,
                names,
                'visDistributionNbdPir'
            );
            plotParameters(
                'SM PIR',
                'Smoothness Predicted In Room (SM PIR) v.s. Score',
                smPIR,
                scores,
                names,
                'visDistributionSmPir'
            );
        }

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
                    return (msr?.computed_sensitivity ?? msr?.sensitivity)?.computed ?? null;
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

        function getUniqueBrands() {
            const brands = new Set();
            metadata.forEach((s) => {
                if (s.brand) brands.add(s.brand);
            });
            return Array.from(brands).sort();
        }

        function populateFilterOptions() {
            const brandSelect = document.getElementById('filterBrand');
            if (brandSelect) {
                const brands = getUniqueBrands();
                brands.forEach((b) => {
                    const opt = document.createElement('option');
                    opt.value = b;
                    opt.textContent = b;
                    brandSelect.appendChild(opt);
                });
            }
            const shapeSelect = document.getElementById('filterShape');
            if (shapeSelect) {
                const shapes = getUniqueShapes();
                shapes.forEach((s) => {
                    const opt = document.createElement('option');
                    opt.value = s;
                    opt.textContent = s;
                    shapeSelect.appendChild(opt);
                });
            }
        }

        function getUniqueShapes() {
            const shapes = new Set();
            metadata.forEach((s) => {
                if (s.shape) shapes.add(s.shape);
            });
            return Array.from(shapes).sort();
        }

        function renderCustomChart() {
            const chartType = document.getElementById('chartType').value;
            const xField = document.getElementById('xAxis').value;
            const yField = document.getElementById('yAxis').value;
            const xScale = document.getElementById('xScale').value;
            const yScale = document.getElementById('yScale').value;
            const colorField = document.getElementById('colorBy').value;
            const filterBrand = document.getElementById('filterBrand').value;
            const filterShape = document.getElementById('filterShape').value;
            const showTrendLine = document.getElementById('showTrendLine')?.checked ?? false;
            const showParetoCurve = document.getElementById('showParetoCurve')?.checked ?? false;

            const supportsCurves = chartType === 'scatter' || chartType === 'bar';

            const histogramOptions = {
                nbins: parseInt(document.getElementById('numBins').value) || 20,
                binSize: parseFloat(document.getElementById('binSize').value) || null,
                start: parseFloat(document.getElementById('binStart').value) || null,
                end: parseFloat(document.getElementById('binEnd').value) || null,
            };

            const data = [];
            const groups = new Map();

            metadata.forEach((speaker) => {
                if (filterBrand && speaker.brand !== filterBrand) return;
                if (filterShape && speaker.shape !== filterShape) return;

                const xVal = getFieldValue(speaker, xField);
                const yVal = getFieldValue(speaker, yField);

                if (xVal === null || yVal === null) return;

                const groupKey = colorField !== 'none' ? getFieldValue(speaker, colorField) : 'all';

                if (!groups.has(groupKey)) {
                    groups.set(groupKey, { x: [], y: [], text: [] });
                }
                groups.get(groupKey).x.push(xVal);
                groups.get(groupKey).y.push(yVal);
                groups.get(groupKey).text.push(speaker.brand + ' ' + speaker.model);
            });

            const colors = [
                '#1f77b4',
                '#ff7f0e',
                '#2ca02c',
                '#d62728',
                '#9467bd',
                '#8c564b',
                '#e377c2',
                '#7f7f7f',
                '#bcbd22',
                '#17becf',
            ];
            let colorIdx = 0;

            groups.forEach((group, key) => {
                const trace = {
                    x: group.x,
                    y: group.y,
                    text: group.text,
                    name: key === 'all' ? 'All' : key,
                };

                if (chartType === 'scatter') {
                    trace.mode = 'markers';
                    trace.type = 'scatter';
                    trace.marker = { size: 8, color: colors[colorIdx % colors.length] };
                } else if (chartType === 'histogram') {
                    trace.type = 'histogram';
                    trace.marker = { color: colors[colorIdx % colors.length] };
                    if (histogramOptions.nbins) {
                        trace.nbinsx = histogramOptions.nbins;
                    }
                    if (histogramOptions.binSize) {
                        trace.xbins = {
                            start: histogramOptions.start,
                            end: histogramOptions.end,
                            size: histogramOptions.binSize,
                        };
                    } else if (histogramOptions.start !== null || histogramOptions.end !== null) {
                        trace.xbins = { start: histogramOptions.start, end: histogramOptions.end };
                    }
                } else if (chartType === 'box') {
                    trace.type = 'box';
                    trace.marker = { color: colors[colorIdx % colors.length] };
                } else if (chartType === 'violin') {
                    trace.type = 'violin';
                    trace.marker = { color: colors[colorIdx % colors.length] };
                } else if (chartType === 'bar') {
                    trace.type = 'bar';
                    trace.marker = { color: colors[colorIdx % colors.length] };
                }

                data.push(trace);
                colorIdx++;
            });

            if (supportsCurves) {
                if (showTrendLine) {
                    const allX = [];
                    const allY = [];
                    groups.forEach((group) => {
                        allX.push(...group.x);
                        allY.push(...group.y);
                    });
                    const regression = computeLinearRegression(allX, allY, {
                        logX: xScale === 'log',
                        logY: yScale === 'log',
                    });
                    if (regression) {
                        data.push({
                            x: regression.x,
                            y: regression.y,
                            mode: 'lines',
                            type: 'scatter',
                            name: 'Trend Line',
                            line: {
                                color: 'black',
                                width: 2,
                                dash: 'dot',
                            },
                            hoverinfo: 'skip',
                        });
                    }
                }

                if (showParetoCurve) {
                    const allX = [];
                    const allY = [];
                    groups.forEach((group) => {
                        allX.push(...group.x);
                        allY.push(...group.y);
                    });

                    const paretoBest = computeParetoCurveForData(allX, allY, { direction: 'max' });
                    if (paretoBest.x.length > 0) {
                        data.push({
                            x: paretoBest.x,
                            y: paretoBest.y,
                            mode: 'lines',
                            type: 'scatter',
                            name: 'Pareto (Best Value)',
                            line: {
                                color: 'red',
                                width: 2,
                                dash: 'dash',
                            },
                            hoverinfo: 'skip',
                        });
                    }

                    const paretoWorst = computeParetoCurveForData(allX, allY, { direction: 'min' });
                    if (paretoWorst.x.length > 0) {
                        data.push({
                            x: paretoWorst.x,
                            y: paretoWorst.y,
                            mode: 'lines',
                            type: 'scatter',
                            name: 'Pareto (Worst Value)',
                            line: {
                                color: 'gray',
                                width: 2,
                                dash: 'dash',
                            },
                            hoverinfo: 'skip',
                        });
                    }
                }
            }

            const xLabel = document.getElementById('xAxis').selectedOptions[0].text;
            const yLabel = document.getElementById('yAxis').selectedOptions[0].text;

            const layout = {
                autosize: true,
                title: { text: `Custom Chart: ${yLabel} vs ${xLabel}` },
                xaxis: { title: xLabel, type: xScale },
                yaxis: { title: chartType === 'histogram' ? 'Count' : yLabel, type: yScale },
                legend: { orientation: 'h', y: -0.2 },
                hovermode: 'closest',
                margin: { l: 50, r: 20, t: 40, b: 40 },
            };

            if (chartType === 'histogram') {
                layout.barmode = 'overlay';
            }

            Plotly.newPlot('visCustomChart', data, layout, { responsive: true });
        }

        function updateHistogramOptions() {
            const chartType = document.getElementById('chartType').value;
            const histOptions = document.getElementById('histogramOptions');
            const curveOptions = document.getElementById('curveOptions');
            if (chartType === 'histogram') {
                histOptions.style.display = 'flex';
            } else {
                histOptions.style.display = 'none';
            }
            if (chartType === 'scatter' || chartType === 'bar') {
                curveOptions.style.display = 'flex';
            } else {
                curveOptions.style.display = 'none';
            }
        }

        document.getElementById('chartType')?.addEventListener('change', updateHistogramOptions);

        function resetCustomChart() {
            document.getElementById('chartType').value = 'scatter';
            document.getElementById('xAxis').value = 'score';
            document.getElementById('yAxis').value = 'score';
            document.getElementById('xScale').value = 'linear';
            document.getElementById('yScale').value = 'linear';
            document.getElementById('colorBy').value = 'none';
            document.getElementById('filterBrand').value = '';
            document.getElementById('filterShape').value = '';
            document.getElementById('numBins').value = 20;
            document.getElementById('binSize').value = '';
            document.getElementById('binStart').value = '';
            document.getElementById('binEnd').value = '';
            document.getElementById('showTrendLine').checked = false;
            document.getElementById('showParetoCurve').checked = false;
            updateHistogramOptions();
            document.getElementById('visCustomChart').innerHTML = '';
        }

        populateFilterOptions();

        document.getElementById('renderCustomChart')?.addEventListener('click', renderCustomChart);
        document.getElementById('resetCustomChart')?.addEventListener('click', resetCustomChart);

        stats();
    })
    .catch((err) => console.log(err.message));
