// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

export function sortMetadata2(metadata, sorter) {
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
        const def = spk.default_measurement;
        const msr = spk.measurements[def];
        // comparing ints (works because 20210101 is bigger than 20201010)
        if ('review_published' in msr) {
            const reviewPublished = parseInt(msr.review_published);
            if (!isNaN(reviewPublished)) {
                return reviewPublished;
            }
        }
        return 19700101;
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
        if ('sensitivity' in spk) {
            return spk.sensitivity;
        }
        return 0.0;
    }

    function getBrandV2(key) {
        const spk = metadata.get(key);
        return spk.brand + ' ' + spk.model;
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
    } else {
        console.log('ERROR: unknown sorter ' + sorter.by);
    }
}
