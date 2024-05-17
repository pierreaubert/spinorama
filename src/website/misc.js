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

// @flow

// hide an element
export const hide = (elem) => {
    if (elem && elem.classList) {
        elem.classList.add('hidden');
    }
};

// show an element
export const show = (elem) => {
    if (elem && elem.classList) {
        elem.classList.remove('hidden');
    }
};

// toggle the element visibility
export const toggle = (elem) => {
    if (elem && elem.classList) {
        elem.classList.toggle('hidden');
    }
};

export function toggleId(id) {
    const elem = document.querySelector(id);
    if (elem && elem.classList) {
        elem.classList.toggle('hidden');
    }
}

export function openModal(elem) {
    if (elem && elem.classList) {
        elem.classList.add('is-active');
    }
}

export function closeModal(elem) {
    if (elem && elem.classList) {
        elem.classList.remove('is-active');
    }
}

function getEQType(type) {
    let val = 'unknown';
    switch (type) {
        case 0:
            val = 'LP';
            break;
        case 1:
            val = 'HP';
            break;
        case 2:
            val = 'BP';
            break;
        case 3:
            val = 'PK';
            break;
        case 4:
            val = 'NO';
            break;
        case 5:
            val = 'LS';
            break;
        case 6:
            val = 'HS';
            break;
    }
    return val;
}

export function getPeq(peq) {
    const peqPrint = [];
    peq.forEach((eq) => {
        peqPrint.push({
            freq: eq.freq,
            dbGain: eq.dbGain,
            Q: eq.Q,
            type: getEQType(eq.type),
        });
    });
    return peqPrint;
}

export function getPicture(brand, model, suffix) {
    return encodeURI('pictures/' + brand + ' ' + model + '.' + suffix);
}

export function removeVendors(str) {
    return str.replace('Vendors-', '');
}

export function getID(brand, model) {
    return (brand + ' ' + model).replace(/['.+& |]/g, '-');
}

export function getPrice(price, amount) {
    const val = parseFloat(price);
    if (isNaN(val)) {
        // console.log('no price')
        return '?';
    }
    if (amount && amount === 'each') {
        // console.log('price each '+price)
        return price;
    }
    // default is per pair
    // console.log('price pair '+price)
    return (val / 2.0).toString();
}

export function getField(value, field, version) {
    let fields = {};
    if (value.measurements && value.measurements[version]) {
        const measurement = value.measurements[version];
        if (Object.hasOwn(measurement, field)) {
            fields = measurement[field];
        }
    }
    return fields;
}

export function getSensitivity(value, version) {
    let init_sensitivity = 0;
    let delta = 0;
    if (value.sensitivity) {
        init_sensitivity = value.sensitivity;
    }
    if (value.measurements && value.measurements[version]) {
        const measurement = value.measurements[version];
        if (Object.hasOwn(measurement, 'sensitivity_delta')) {
            delta = measurement.sensitivity_delta;
        }
    }
    const sensitivity = init_sensitivity + delta;
    if (sensitivity !== 0.0) {
        // console.log(value.brand+' sensitivity='+sensitivity)
        return sensitivity;
    }
    return undefined;
}

export function getReviews(value) {
    const reviews = [];
    for (const version in value.measurements) {
        const measurement = value.measurements[version];
        let origin = measurement.origin;
        let originLong = measurement.origin;
        let originShort = measurement.origin;
        const url = 'speakers/' + value.brand + ' ' + value.model + '/' + removeVendors(origin) + '/index_' + version + '.html';
        if (origin === 'Misc') {
            origin = version.replace('misc-', '');
            originShort = version.replace('misc-', '');
            originLong = version.replace('misc-', '');
        } else {
            origin = origin.replace('Vendors-', '');
            originShort = origin.replace('Vendors-', '');
            originLong = origin.replace('Vendors-', '');
        }
        if (origin === 'Princeton') {
            origin = 'Princeton';
            originShort = 'Pri.';
        } else if (origin === 'napilopez') {
            origin = 'Napilopez';
            originShort = 'Nap.';
        } else if (origin === 'speakerdata2034') {
            origin = 'SpeakerData2034';
            originShort = 'SPD.';
        } else if (origin === 'archimago') {
            origin = 'Archimago';
            originShort = 'Arc.';
        } else if (origin === 'audioxpress') {
            origin = 'AudioXPress';
            originShort = 'Axp.';
        } else if (origin === 'audioholics') {
            origin = 'audioholics';
            originShort = 'Aud.';
        } else if (origin === 'soundstageultra') {
            origin = 'Sound Stage Ultra';
            originShort = 'SSU.';
        } else if (origin === 'sr') {
            origin = 'Sound & Recordings';
            originShort = 'S&R';
        } else if (origin.search('nuyes') !== -1) {
            origin = 'Nuyes';
            originShort = 'Nuy.';
        } else if (origin.search('ASR') !== -1) {
            origin = 'Audio Science Review';
            originShort = 'ASR';
        } else if (origin.search('ErinsAudioCorner') !== -1) {
            origin = "Erin's Audio Corner";
            originShort = 'EAC';
        }

        origin = origin.charAt(0).toUpperCase() + origin.slice(1);
        originLong = originLong.charAt(0).toUpperCase() + origin.slice(1);
        if (version.search('sealed') !== -1) {
            origin = origin + ' (Sealed)';
            originLong = originLong + ' (Sealed)';
            originShort = originShort + ' (S)';
        } else if (version.search('vented') !== -1) {
            origin = origin + ' (Vented)';
            originShort = originShort + ' (V)';
            originLong = originLong + ' (Vented)';
        } else if (version.search('ported') !== -1) {
            origin = origin + ' (Ported)';
            originShort = originShort + ' (P)';
            originLong = originLong + ' (Ported)';
        }

        if (version.search('grille-on') !== -1) {
            origin = origin + ' (Grille on)';
            originShort = originShort + ' (Gon)';
            originLong = originLong + ' (Grille on)';
        } else if (version.search('no-grille') !== -1) {
            origin = origin + ' (Grille off)';
            originShort = originShort + ' (Gof)';
            originLong = originLong + ' (Grille off)';
        }

        if (version.search('short-port') !== -1) {
            origin = origin + ' (Short Port)';
            originShort = originShort + ' (sP)';
            originLong = originLong + ' (Short Port)';
        } else if (version.search('long-port') !== -1) {
            origin = origin + ' (Long Port)';
            originShort = originShort + ' (lP)';
            originLong = originLong + ' (Long Port)';
        }

        if (version.search('bassreflex') !== -1) {
            origin = origin + ' (BR)';
            originShort = originShort + ' (BR)';
            originLong = originLong + ' (Bass Reflex)';
        } else if (version.search('cardioid') !== -1) {
            origin = origin + ' (C)';
            originShort = originShort + ' (C)';
            originLong = originLong + ' (Cardiod)';
        }

        if (version.search('fullrange') !== -1) {
            origin = origin + ' (FR)';
            originShort = originShort + ' (FR)';
            originLong = originLong + ' (Full Range)';
        } else if (version.search('lowcut') !== -1) {
            origin = origin + ' (LC)';
            originShort = originShort + ' (LC)';
            originLong = originLong + ' (Low Cut)';
        }

        if (version.search('active') !== -1) {
            origin = origin + ' (Act.)';
            originLong = originLong + ' (Active)';
        } else if (version.search('passive') !== -1) {
            origin = origin + ' (Pas.)';
            originLong = originLong + ' (Passive)';
        }

        if (version.search('horizontal') !== -1) {
            origin = origin + ' (Hor.)';
            originShort = originShort + ' (Ho)';
            originLong = originLong + ' (Horizontal)';
        } else if (version.search('vertical') !== -1) {
            origin = origin + ' (Ver.)';
            originShort = originShort + ' (Ve)';
            originLong = originLong + ' (Vertical)';
        }

        if (version.search('gll') !== -1) {
            origin = origin + ' (gll)';
            originShort = originShort + ' (gll)';
            originLong = originLong + ' (gll)';
        } else if (version.search('klippel') !== -1) {
            origin = origin + ' (klippel)';
            originShort = originShort + ' (nfs)';
            originLong = originLong + ' (klippel)';
        }

        if (version.search('wide') !== -1) {
            origin = origin.slice(0, origin.length - 1) + '/W)';
            originShort = originShort + ' (/W)';
            originLong = originLong.slice(0, originLong.length - 1) + '/Wide)';
        } else if (version.search('narrow') !== -1) {
            origin = origin.slice(0, origin.length - 1) + '/N)';
            originShort = originShort + ' (/N)';
            originLong = originLong.slice(0, originLong.length - 1) + '/Narrow)';
        } else if (version.search('medium') !== -1) {
            origin = origin.slice(0, origin.length - 1) + '/M)';
            originShort = originShort + ' (/M)';
            originLong = originLong.slice(0, originLong.length - 1) + '/Medium)';
        }

        if (version.search('Gecko') !== -1) {
            origin = origin + ' (Gecko)';
            originLong = originLong + ' (Gecko)';
        } else if (version.search('Tree') !== -1) {
            origin = origin + ' (Tree)';
            originLong = originLong + ' (Tree)';
        } else if (version.search('Pod') !== -1) {
            origin = origin + ' (Pod)';
            originLong = originLong + ' (Pod)';
        }

        const ipattern = version.search('pattern');
        if (ipattern !== -1) {
            const sversion = version.slice(ipattern + 8);
            if (sversion.search(/[0-9]*/) !== -1) {
                const sversionTimes = sversion.indexOf('x');
                let sversionDeg = sversion;
                if (sversionTimes !== -1) {
                    const verticalAngle = sversion.slice(sversionTimes);
                    const dashPos = verticalAngle.indexOf('-');
                    if (dashPos === -1) {
                        sversionDeg = ' ' + sversion.slice(0, sversionTimes) + 'º' + sversion.slice(sversionTimes) + 'º';
                    } else {
                        sversionDeg = ' ' + sversion.slice(0, sversionTimes) + 'º' + verticalAngle.slice(0, dashPos) + 'º';
                    }
                } else {
                    sversionDeg = ' ' + sversion + 'º';
                }
                origin = origin + sversionDeg;
                originLong = originLong + sversionDeg;
            }
        }

        // version
        const posVersion = version.search(/-v[123456]-/);
        if (posVersion !== -1) {
            origin = origin + ' (v' + version[posVersion + 2] + ')';
            originLong = originLong + ' (v' + version[posVersion + 2] + ')';
        }

        // counter
        const posCounter = version.search(/-v[123456]x/);
        if (posCounter !== -1) {
            origin = origin + ' (' + version[posCounter + 2] + 'x)';
            originLong = originLong + ' (' + version[posCounter + 2] + 'x)';
        }

        // configuration
        const posConfiguration = version.search(/-configuration-/);
        if (posConfiguration !== -1) {
            origin = origin + ' (' + version.slice(posConfiguration + 14).replace('-', ' ') + ')';
            originLong = originLong + ' (' + version.slice(posConfiguration + 14).replace('-', ' ') + ')';
        }

        // angree
        const posDegrees = version.search(/10-degrees/);
        if (posDegrees !== -1) {
            origin = origin + ' (10°)';
            originLong = originLong + ' (10°)';
        }

        reviews.push({
            url: encodeURI(url),
            origin: origin,
            originShort: originShort,
            originLong: originLong,
            version: version,
            scores: getField(value, 'pref_rating', version),
            scoresEq: getField(value, 'pref_rating_eq', version),
            estimates: getField(value, 'estimates', version),
            extras: getField(value, 'extras', version),
            specifications: getField(value, 'specifications', version),
            estimatesEq: getField(value, 'estimates_eq', version),
            sensitivity: getSensitivity(value, version),
        });
    }
    return {
        reviews: reviews,
    };
}

export function getScore(value, def) {
    if (def) {
        def = value.default_measurement;
    }
    let score = 0.0;
    let lfx = 0.0;
    let flatness = 0.0;
    let smoothness = 0.0;
    let scoreScaled = 0.0;
    let lfxScaled = 0.0;
    let flatnessScaled = 0.0;
    let smoothnessScaled = 0.0;
    if (value.measurements && value.measurements[def].pref_rating) {
        const measurement = value.measurements[def];
        const pref = measurement.pref_rating;
        score = pref.pref_score;
        if (pref.lfx_hz) {
            lfx = pref.lfx_hz;
        }
        smoothness = pref.sm_pred_in_room;
        const prefScaled = measurement.scaled_pref_rating;
        scoreScaled = prefScaled.scaled_pref_score;
        if (prefScaled.scaled_lfx_hz) {
            lfxScaled = prefScaled.scaled_lfx_hz;
        }
        smoothnessScaled = prefScaled.scaled_sm_pred_in_room;

        const estimates = measurement.estimates;
        if (estimates && estimates.ref_band) {
            flatness = estimates.ref_band;
        }
        flatnessScaled = prefScaled.scaled_flatness;
    }
    let specifications = {};
    if (value.measurements && value.measurements[def].specifications) {
        specifications = value.measurements[def].specifications;
    }
    return {
        score: parseFloat(score).toFixed(1),
        lfx: lfx.toFixed(0),
        flatness: flatness.toFixed(1),
        smoothness: smoothness.toFixed(1),
        scoreScaled: scoreScaled.toFixed(1),
        lfxScaled: lfxScaled,
        flatnessScaled: flatnessScaled,
        smoothnessScaled: smoothnessScaled,
        specifications: specifications,
    };
}

export function getLoading(key) {
    if (key < 12) {
        return 'eager';
    }
    return 'lazy';
}

export function getDecoding(key) {
    if (key < 12) {
        return 'sync';
    }
    return 'async';
}
