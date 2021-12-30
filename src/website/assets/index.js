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
