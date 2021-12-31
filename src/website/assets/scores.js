fetch(urlSite+'assets/metadata.json').then(
    function(response) {
	return response.json();
    }).then( (datajs) => {

	var speakerContainer = document.querySelector('[data-num="0"');
	const speakerDatabase = Object.values(datajs);

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
                reviews: getReviews(value),
                img: {
                    avif: getPicture(value.brand, value.model, "avif"),
                    webp: getPicture(value.brand, value.model, "webp"),
                    jpg: getPicture(value.brand, value.model, "jpg"),
                    loading: getLoading(key),
                    decoding: getDecoding(key),
                },
            };
        }

        function plotRadar(key, value, id) {
            const data = [{
                type: 'scatterpolar',
                r: [39, 28, 8, 7, 28, 39],
                theta: ['A','B','C', 'D', 'E', 'A'],
                fill: 'toself'
            }];

            const layout = {
                polar: {
                    radialaxis: {
                        visible: true,
                        range: [0, 50]
                    }
                },
                showlegend: false
            };

            Plotly.newPlot(id+'-plot', data, layout);
        }

        function printScore(key, value) {
            const source = document.querySelector('#scoresht').innerHTML;
            var template = Handlebars.compile(source);
            var context = getContext(key, value);
            var html = template(context);
            var divScore = document.createElement('div');
            divScore.setAttribute("id", context.id);
            divScore.setAttribute("class", "column is-12 is-vertical");
            divScore.innerHTML = html;
            return divScore;
        }

        function display () {
            var fragment1 = new DocumentFragment();
	    speakerDatabase.forEach( function(value, key) {
                fragment1.appendChild(printScore(key, value));
	    });
            sort_metadata(speakerDatabase, fragment1, {by: "score"});
            speakerContainer.appendChild(fragment1);

	    //speakerDatabase.forEach( function(value, key) {
            //    context = getContext(key,value);
            //    plotRadar(key, value, context.id);
            //});
        }

        display();
    });
