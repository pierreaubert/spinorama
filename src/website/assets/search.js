const urlSite = '${site}'+'/';

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

fetch(urlSite+'assets/metadata.json').then(
    function(response) {
	return response.text();
    }).then( (datajs) => {

        // console.log("got json");
        let metadata = Object.values(JSON.parse(datajs));
        // build a hash map
        let indirect = {};
        for (let item in metadata) {
            var key = (metadata[item].brand+'-'+metadata[item].model).replace(/['.+& ]/g, "-");
            indirect[key] = item;
            // console.log('adding '+key);
        }
        // console.log("got metadata");
        let resultdiv = document.querySelector("div.searchresults");

        let filter = {
	    reviewer: "",
	    shape: "",
	    power: "",
	    brand: "",
	    quality: "",
        };

        let sorter = {
	    by: "",
        };

        function selectDispatch() {
	    let keywords = document.querySelector("#searchInput").value;
	    // console.log("keywords: "+keywords);
            sort_metadata(sorter);

	    if (keywords === "") {
                // console.log("display filter");
                display_filter(resultdiv, metadata, filter);
	    } else {
                // console.log("display search");
	        const fuse = new Fuse(metadata, {
	            isCaseSensitive: false,
	            matchAllTokens: true,
	            findAllMatches: true,
	            minMatchCharLength: 2,
	            keys: ["brand", "model"],
	            treshhold: 0.5,
	            distance: 4,
	            includeScore: true,
	            useExatendedSearch: true
	        });
                let results = fuse.search(keywords);
                display_search(resultdiv, metadata, results, filter);
	    }
	    show(resultdiv);
        }

        document.querySelector("#selectReviewer").addEventListener("change", function () {
	    filter["reviewer"] = this.value;
	    selectDispatch();
        });

        document.querySelector("#selectQuality").addEventListener("change", function () {
	    filter["quality"] = this.value;
	    selectDispatch();
        });

        document.querySelector("#selectShape").addEventListener("change", function () {
	    filter["shape"] = this.value;
	    selectDispatch();
        });

        document.querySelector("#selectPower").addEventListener("change", function () {
	    filter["power"] = this.value;
	    selectDispatch();
        });

        document.querySelector("#selectBrand").addEventListener("change", function () {
	    filter["brand"] = this.value;
	    selectDispatch();
        });

        document.querySelector("#sortBy").addEventListener("change", function () {
	    sorter["by"] = this.value;
	    selectDispatch();
        });

        document.querySelector("#searchInput").addEventListener("keyup", function () {
	    selectDispatch();
        });

        function is_filtered(item, filter) {
	    let show = true;
	    if (filter.reviewer !== "" ) {
                let found = true;
	        for (let [name, measurement] of Object.entries(item["measurements"])) {

                    let origin = measurement["origin"].toLowerCase();
                    // console.log("debug: name="+name+" origin="+origin+" filter.reviewer="+filter.reviewer);
                    if (name.toLowerCase().endsWith(filter.reviewer.toLowerCase()) || origin == filter.reviewer.toLowerCase()) {
                        found = false;
                        break;
                    }
                }
                if(found) {
                    show = false;
                }
	    }
            // console.log("debug: name="+name+" post filter reviewer "+show)
	    if (filter.quality !== "" ) {
                let found = true;
	        for (let [name, measurement] of Object.entries(item["measurements"])) {

                    let quality = measurement["quality"].toLowerCase();
                    // console.log("filter.quality="+filter.quality+" quality="+quality);
                    if (filter.quality !== "" && quality == filter.quality.toLowerCase()) {
		        found = false;
                        break;
	            }
                }
                if(found) {
                    show = false;
                }
	    }
            // console.log("debug: name="+name+" post quality "+show)
	    if (filter.power !== "" && item.type !== filter.power) {
                show = false;
	    }
            // console.log("debug: name="+name+" post power "+show)
	    if (filter.shape !== "" && item.shape !== filter.shape) {
                show = false;
	    }
            // console.log("debug: name="+name+" post shape "+show)
	    if (filter.brand !== "" && item.brand.toLowerCase() !== filter.brand.toLowerCase()) {
                show = false;
	    }
            // console.log("debug: name="+name+" post brand "+show)
	    return show;
        }

        function display_filter(resultdiv, sorted_meta, filter) {
	    // console.log("display filter start #" + sorted_meta.length);
	    for (const item in sorted_meta) {
                let show = is_filtered(sorted_meta[item], filter);
                const id = (sorted_meta[item].brand + "-" + sorted_meta[item].model).replace(/['.+& ]/g, "-");
                if (show) {
                    // console.log(sorted_meta[item].brand + "-"+ sorted_meta[item].model + " is shown");
		    show(document.querySelector("#" + id));
                } else {
                    // console.log(sorted_meta[item].brand + "-"+ sorted_meta[item].model + " is filtered");
		    hide(document.querySelector("#" + id));
                }
	    }
        }

        function display_search(resultdiv, sorted_meta, results, filter) {
	    // console.log("---------- display search start ----------------");
            let keywords = document.querySelector("#searchInput").value;
	    if (results.length === 0) {
                display_filter(resultdiv, sorted_meta, filter);
                return;
	    }
	    // hide all
	    for (const item in sorted_meta) {
                const id = (sorted_meta[item].brand + "-" + sorted_meta[item].model).replace(/['.+& ]/g, "-");
                hide(document.querySelector("#" + id));
	    }
	    // minScore
	    let minScore = 1;
	    for (const item in results) {
                if (results[item].score < minScore) {
		    minScore = results[item].score;
                }
	    }
	    // console.log("minScore is "+minScore);
	    for (let item in results) {
                let shouldShow = true;
                let result = results[item];
                let item_meta = result.item;
                let score = result.score;
                // console.log("evaluating "+item_meta.brand+" "+item_meta.model+" "+score);
                if (!is_filtered(item_meta, filter)) {
		    // console.log("filtered out (filter)");
		    shouldShow = false;
                }
                if (shouldShow) {
		    if (minScore < Math.pow(10, -15)) {
                        let is_exact = item_meta.model.toLowerCase().includes(keywords.toLowerCase());
                        // we have an exact match, only shouldShow other exact matches
                        if (score >= Math.pow(10, -15) && !is_exact) {
		            // console.log("filtered out (minscore)" + score);
			    shouldShow = false;
                        }
		    } else {
                        // only partial match
                        if (score > minScore*10) {
		            // console.log("filtered out (score="+score+"minscore="+minScore+")");
			    shouldShow = false;
                        }
		    }
                }
                const id = (item_meta.brand + "-" + item_meta.model).replace(/['.+& ]/g, "-");
                if (shouldShow) {
		    // console.log("show "+item_meta.brand+" "+item_meta.model+" "+score);
		    show(document.querySelector("#" + id));
                } else {
		    // console.log("hide "+item_meta.brand+" "+item_meta.model+" "+score);
		    hide(document.querySelector("#" + id));
                }

	    }
        }

        function get_price(item) {
            if (item.id in indirect) {
                let price = parseInt(metadata[indirect[item.id]].price);
                if (!isNaN(price)) {
                    return price;
                }
            }
            return -1;
        }

        function get_score(item) {
            if (item.id in indirect) {
                let meta = metadata[indirect[item.id]];
                let def  = meta.default_measurement;
                let msr  = meta.measurements[def];
                if ('pref_rating' in msr && 'pref_score' in msr.pref_rating) {
                    // console.log(item, meta.measurements[def].pref_rating.pref_score);
                    return meta.measurements[def].pref_rating.pref_score;
                }
            }
            // console.log(item, -10);
            return -10.0;
        }

        function get_score_wsub(item) {
            if (item.id in indirect) {
                let meta = metadata[indirect[item.id]];
                let def  = meta.default_measurement;
                let msr  = meta.measurements[def];
                if ('pref_rating' in msr && 'pref_score_wsub' in msr.pref_rating) {
                    // console.log(item, meta.measurements[def].pref_rating.pref_score);
                    return meta.measurements[def].pref_rating.pref_score_wsub;
                }
            }
            // console.log(item, -10);
            return -10.0;
        }

        function get_score_eq(item) {
            if (item.id in indirect) {
                let meta = metadata[indirect[item.id]];
                let def  = meta.default_measurement;
                let msr  = meta.measurements[def];
                if ('pref_rating_eq' in msr && 'pref_score' in msr.pref_rating) {
                    return meta.measurements[def].pref_rating_eq.pref_score;
                }
            }
            return -10.0;
        }

        function get_score_eq_wsub(item) {
            if (item.id in indirect) {
                let meta = metadata[indirect[item.id]];
                let def  = meta.default_measurement;
                let msr  = meta.measurements[def];
                if ('pref_rating_eq' in msr && 'pref_score_wsub' in msr.pref_rating) {
                    return meta.measurements[def].pref_rating_eq.pref_score_wsub;
                }
            }
            return -10.0;
        }

        function get_date(item) {
            if (item.id in indirect) {
                let meta = metadata[indirect[item.id]];
                let def  = meta.default_measurement;
                let msr  = meta.measurements[def];
                // comparing ints (works because 20210101 is bigger than 20201010)
                if ('review_published' in msr) {
                    let review_published  = parseInt(msr.review_published);
                    if (!isNaN(review_published)) {
                        return review_published;
                    }
                }
            }
            return 19700101;
        }

        function sort_metadata(current_sorter) {
            // console.log("starting sort + sort_by:"+current_sorter.by);
            // TODO build once
            let sorted = {};
            if (current_sorter.by === 'price') {
                sorted = document.querySelector("div.searchresults > div > div").sort( function(a, b) {
                    return get_price(b)-get_price(a);
                });
            } else if (current_sorter.by === 'score') {
                sorted = document.querySelector("div.searchresults > div > div").sort( function(a, b) {
                    return get_score(b)-get_score(a);
                });
            } else if (current_sorter.by === 'scoreEQ') {
                sorted = document.querySelector("div.searchresults > div > div").sort( function(a, b) {
                    return get_score_eq(b)-get_score_eq(a);
                });
            } else if (current_sorter.by === 'scoreWSUB') {
                sorted = document.querySelector("div.searchresults > div > div").sort( function(a, b) {
                    return get_score_wsub(b)-get_score_wsub(a);
                });
            } else if (current_sorter.by === 'scoreEQWSUB') {
                sorted = document.querySelector("div.searchresults > div > div").sort( function(a, b) {
                    return get_score_eq_wsub(b)-get_score_eq_wsub(a);
                });
            } else if (current_sorter.by === 'date') {
                sorted = document.querySelector("div.searchresults > div > div").sort( function(a, b) {
                    return get_date(b)-get_date(a);
                });
            } else {
                // console.log('Error sort method is unkown: '+current_sorter.by);
            }

            // overrides
            if ( sorted.length > 1 ) {
	        document.querySelector("div.searchresults > div").html(sorted);
            }
        }

    });
