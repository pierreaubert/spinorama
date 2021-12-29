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

        function getContext(key, value) {
            // console.log(getReviews(value));
            return {
                id: getID(value.brand,value.model),
                brand: value.brand,
                model: value.model,
                autoeq: 'https://raw.githubusercontent.com/pierreaubert/spinorama/develop/datas/eq/'+
                    encodeURI(value.brand+' '+value.model)+
                    '/iir-autoeq.txt',
                preamp_gain: value["eq_autoeq"]['preamp_gain'],
                peq: getPeq(value["eq_autoeq"]['peq']),
            };
        }

        function printEQ(key, value) {
            const source = document.querySelector('#eqsht').innerHTML;
            var template = Handlebars.compile(source);
            var context = getContext(key, value);
            var html = template(context);
            var divEQ = document.createElement('div');
            divEQ.setAttribute("class", "column is-one-third");
            divEQ.setAttribute("id", context.id);
            divEQ.innerHTML = html;
            return divEQ;
        }

        function display () {
            var fragment1 = new DocumentFragment();
	    speakerDatabase.forEach( function(value, key) {
                if ('eq_autoeq' in value) {
                    fragment1.appendChild(printEQ(key, value));
                }
	    });
            sort_metadata(speakerDatabase, fragment1, {by: "score"});
            speakerContainer.appendChild(fragment1);
        }

        display();
    });
