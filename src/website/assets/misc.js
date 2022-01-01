// hide an element
const hide = (elem) => {
    elem.classList.add('hidden');
}

// show an element
const show = (elem) => {
    elem.classList.remove('hidden');
}

// toggle the element visibility
const toggle = (elem) => {
    elem.classList.toggle('hidden');
}
const toggleId = (id) => {
    elem = document.querySelector(id);
    if (elem && elem.classList) {
        elem.classList.toggle('hidden');
    }
}

function getEQType(type) {
    var val='unknown';
    switch(type) {
    case 0: val = 'LP'; break;
    case 1: val = 'HP'; break;
    case 2: val = 'BP'; break;
    case 3: val = 'PK'; break;
    case 4: val = 'NO'; break;
    case 5: val = 'LS'; break;
    case 6: val = 'HS'; break;
    }
    return val;
}

function getPeq(peq) {
    var peqPrint = [];
    peq.forEach( (eq) => {
        peqPrint.push({
            freq: eq.freq,
            dbGain: eq.dbGain,
            Q: eq.Q,
            type: getEQType(eq.type),
        });
    });
    return peqPrint;
}

function getPicture(brand, model, suffix) {
    return encodeURI('pictures/' + brand + ' ' + model + '.' + suffix);
}

function removeVendors(str) {
    return str.replace("Vendors-", "");
}

function getID(brand, model) {
    return (brand + ' ' + model).replace(/['.+& ]/g, "-");
}

function getField(value, field) {
    var fields = {};
    if (value.default_measurement) {
        var current = value.default_measurement;
        if (value.measurements && value.measurements[current]) {
            var measurement = value.measurements[current];
            if (measurement.hasOwnProperty(field)) {
                fields = measurement[field];
            }
        }
    }
    return fields;
}

function getReviews(value) {
    var reviews = [];
    const version = value.default_measurement;
    for (let version in value.measurements) {
        var measurement =  value.measurements[version];
        var origin = measurement.origin;
        var url = value.brand + ' ' + value.model + '/' + removeVendors(origin) + '/index_' + version + '.html';
        if (origin == 'Misc') {
            origin = version.replace("misc-", "");
        } else {
            origin = origin.replace("Vendors-", "");
        }
        if (origin == 'ErinsAudioCorner') {
            origin = 'EAC';
        } else if ( origin == 'Princeton' ) {
            origin = '3D3A';
        } else if ( origin == 'napilopez') {
            origin = 'NPZ';
        } else if ( origin == 'speakerdata2034') {
            origin = 'SPD';
        }
        origin = origin.charAt(0).toUpperCase() + origin.slice(1);
        reviews.push({
            url: encodeURI(url),
            origin: origin,
        });
    }
    return {
        reviews: reviews,
    };
}

function getScore(value) {
    const def = value.default_measurement;
    var score = 0.0;
    var lfx = 0.0;
    var flatness = 0.0;
    var smoothness = 0.0;
    var scoreScaled = 0.0;
    var lfxScaled = 0.0;
    var flatnessScaled = 0.0;
    var smoothnessScaled = 0.0;
    if ( value.measurements &&
         value.measurements[def].pref_rating) {
        var measurement = value.measurements[def];
        var pref = measurement.pref_rating;
        score = pref.pref_score;
        if (pref.lfx_hz) {
            lfx = pref.lfx_hz;
        }
        smoothness = pref.sm_pred_in_room;
        var prefScaled = measurement.scaled_pref_rating;
        scoreScaled = prefScaled.scaled_pref_score;
        if (prefScaled.scaled_lfx_hz) {
            lfxScaled = prefScaled.scaled_lfx_hz;
        }
        smoothnessScaled = prefScaled.scaled_sm_pred_in_room;

        var estimates = measurement.estimates;
        if ( estimates && estimates.ref_band ) {
            flatness = estimates.ref_band;
        }
        flatnessScaled = prefScaled.scaled_flatness;
    }
    return {
        score: parseFloat(score).toFixed(1),
        lfx: lfx.toFixed(0),
        flatness: flatness.toFixed(1),
        smoothness: smoothness.toFixed(1),
        scoreScaled : scoreScaled.toFixed(1),
        lfxScaled: lfxScaled,
        flatnessScaled: flatnessScaled,
        smoothnessScaled: smoothnessScaled,
    };
}

function getLoading(key) {
    if (key < 12 ) {
        return "eager";
    }
    return "lazy";
}

function getDecoding(key) {
    if (key < 12 ) {
                return "sync";
    }
    return "async";
}
