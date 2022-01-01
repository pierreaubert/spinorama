fetch(urlSite+'assets/metadata.json').then(
    function(response) {
	return response.json();
    }).then( (datajs) => {

	var speakerContainer = document.querySelector('[data-num="0"');
	const speakerDatabase = Object.values(datajs);

        function getSpider(brand, model) {
            // console.log(brand + model);
            return encodeURI(brand + ' ' + model + '/spider.jpg');
        }

        function getContext(key, value) {
            // console.log(getReviews(value));
            var scores = getField(value, 'pref_rating');
            scores['pref_score'] = parseFloat(scores['pref_score']).toFixed(1);
            scores['pref_score_wsub'] = parseFloat(scores['pref_score_wsub']).toFixed(1);
            var scores_eq = getField(value, 'pref_rating_eq');
            scores_eq['pref_score'] = parseFloat(scores['pref_score']).toFixed(1);
            scores_eq['pref_score_wsub'] = parseFloat(scores['pref_score_wsub']).toFixed(1);
            return {
                id: getID(value.brand, value.model),
                brand: value.brand,
                model: value.model,
                sensitivity: value.sensitivity,
                estimates: getField(value, 'estimates'),
                estimates_eq: getField(value, 'estimates_eq'),
                scores: scores,
                scores_eq: scores_eq,
                reviews: getReviews(value),
                img: {
                    // avif: getPicture(value.brand, value.model, "avif"),
                    webp: getPicture(value.brand, value.model, "webp"),
                    jpg: getPicture(value.brand, value.model, "jpg"),
                    loading: getLoading(key),
                    decoding: getDecoding(key),
                },
                spider: getSpider(value.brand, value.model),
            };
        }

        function printScore(key, value) {
            const source = document.querySelector('#scoresht').innerHTML;
            var template = Handlebars.compile(source);
            var context = getContext(key, value);
            var html = template(context);
            var divScore = document.createElement('div');
            divScore.setAttribute("id", context.id);
            divScore.setAttribute("class", "column py-0 is-12 is-vertical");
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

        }

        display();
    });
