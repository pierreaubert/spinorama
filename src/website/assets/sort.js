const urlSite = '${site}'+'/';

function sort_metadata(currentMetadata, currentContainer, current_sorter) {
    // console.log("starting sort + sort_by:"+current_sorter.by);
    // TODO build once
    // build a hash map
    var indirectMetadata = {};
    for (let item in currentMetadata) {
        var key = (currentMetadata[item].brand+'-'+currentMetadata[item].model).replace(/['.+& ]/g, "-");
        indirectMetadata[key] = item;
        // console.log('adding '+key);
    }

    // sort children
    const sortChildren = ({container, getScore }) => {
        const items = [...container.children];
        items.sort((a, b) => getScore(b) - getScore(a)).forEach(item => container.appendChild(item));
    };

    function get_price(item) {
        if (item.id in indirectMetadata) {
            let price = parseInt(currentMetadata[indirectMetadata[item.id]].price);
            if (!isNaN(price)) {
                return price;
            }
        }
        return -1;
    }

    function get_score(item) {
        if (item.id in indirectMetadata) {
            let meta = currentMetadata[indirectMetadata[item.id]];
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
        if (item.id in indirectMetadata) {
            let meta = currentMetadata[indirectMetadata[item.id]];
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
        if (item.id in indirectMetadata) {
            let meta = currentMetadata[indirectMetadata[item.id]];
            let def  = meta.default_measurement;
            let msr  = meta.measurements[def];
            if ('pref_rating_eq' in msr && 'pref_score' in msr.pref_rating) {
                return meta.measurements[def].pref_rating_eq.pref_score;
            }
        }
        return -10.0;
    }

    function get_score_eq_wsub(item) {
        if (item.id in indirectMetadata) {
            let meta = currentMetadata[indirectMetadata[item.id]];
            let def  = meta.default_measurement;
            let msr  = meta.measurements[def];
            if ('pref_rating_eq' in msr && 'pref_score_wsub' in msr.pref_rating) {
                return meta.measurements[def].pref_rating_eq.pref_score_wsub;
            }
        }
        return -10.0;
    }

    function get_date(item) {
        if (item.id in indirectMetadata) {
            let meta = currentMetadata[indirectMetadata[item.id]];
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

    if (current_sorter.by === 'price') {
        sortChildren({
            container: currentContainer,
            getScore: item => {
                return get_price(item);
            }
        });
    } else if (current_sorter.by === 'score') {
        sortChildren({
            container: currentContainer,
            getScore: item => {
                return get_score(item);
            }
        });
    } else if (current_sorter.by === 'scoreEQ') {
        sortChildren({
            container: currentContainer,
            getScore: item => {
                return get_score_eq(item);
            }
        });
    } else if (current_sorter.by === 'scoreWSUB') {
        sortChildren({
            container: currentContainer,
            getScore: item => {
                return get_score_wsub(item);
            }
        });
    } else if (current_sorter.by === 'scoreEQWSUB') {
        sortChildren({
            container: currentContainer,
            getScore: item => {
                return get_score_eq_wsub(item);
            }
        });
    } else if (current_sorter.by === 'date') {
        sortChildren({
            container: currentContainer,
            getScore: item => {
                return get_date(item);
            }
        });
    } else {
        console.log('Error sort method is unkown: '+current_sorter.by);
    }
    return currentMetadata;
}
