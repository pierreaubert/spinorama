fetch(urlSite+'assets/metadata.json').then(
    function(response) {
	return response.json();
    }).then( (datajs) => {

	var speakerContainer = document.querySelector('[data-num="0"');
	const speakerDatabase = Object.values(datajs);

        function getPicture(brand, model, suffix) {
            return encodeURI('pictures/' + brand + ' ' + model + '.' + suffix);
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
                score: score,
                lfx: lfx,
                flatness: flatness,
                smoothness: smoothness,
                scoreScaled : scoreScaled,
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

        function removeVendors(str) {
            return str.replace("Vendors-", "");
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

        function getID(brand, model) {
            return (brand + ' ' + model).replace(/['.+& ]/g, "-");
        }

        function getContext(key, value) {
            // console.log(getReviews(value));
            return {
                id: getID(value.brand,value.model),
                brand: value.brand,
                model: value.model,
                img: {
                    avif: getPicture(value.brand, value.model, "avif"),
                    webp: getPicture(value.brand, value.model, "webp"),
                    jpg: getPicture(value.brand, value.model, "jpg"),
                    loading: getLoading(key),
                    decoding: getDecoding(key),
                },
                score: getScore(value),
                reviews: getReviews(value),
            };
        }

        function printSpeaker(key, value) {
            const source = document.querySelector('#speaker').innerHTML;
            var template = Handlebars.compile(source);
            var context = getContext(key, value);
            var html = template(context);
            var divSpeaker = document.createElement('div');
            divSpeaker.setAttribute("class", "column is-2");
            divSpeaker.setAttribute("id", context.id);
            divSpeaker.innerHTML = html;
            return divSpeaker;
        }

        function display () {
            var fragment1 = new DocumentFragment();
	    speakerDatabase.forEach( function(value, key) {
                fragment1.appendChild(printSpeaker(key, value));
	    });
            sort_metadata(speakerDatabase, fragment1, {by: "date"});
            speakerContainer.appendChild(fragment1);
        }

        display();
    });
