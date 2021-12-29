fetch(urlSite+'assets/metadata.json').then(
    function(response) {
	return response.json();
    }).then( (datajs) => {

	var speakerContainer = document.querySelector('[data-num="0"');
	const speakerDatabase = Object.values(datajs);

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

        function getContext(key, value) {
            // console.log(getReviews(value));
            return {
                id: getID(value.brand,value.model),
                brand: value.brand,
                model: value.model,
                sensitivity: value.sensitivity,
                estimates: getField(value, 'estimates'),
                estimates_eq: getField(value, 'estimates_eq'),
                scores: getField(value, 'pref_rating'),
                scores_eq: getField(value, 'pref_rating_eq'),
            };
        }

        function printScore(key, value) {
            const source = document.querySelector('#scoresht').innerHTML;
            var template = Handlebars.compile(source);
            var context = getContext(key, value);
            var html = template(context);
            var divEQ = document.createElement('div');
            divEQ.setAttribute("class", "column is-12 is-vertical");
            divEQ.setAttribute("id", context.id);
            divEQ.innerHTML = html;
            return divEQ;
        }

        function display () {
            var fragment1 = new DocumentFragment();
	    speakerDatabase.forEach( function(value, key) {
                fragment1.appendChild(printScore(key, value));
	    });
            sort_metadata(speakerDatabase, fragment1, {by: "score"});
            speakerContainer.appendChild(fragment1);
        }

        display();
    });
