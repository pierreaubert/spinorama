window.$ = window.jQuery;

$(document).ready(function () {

    window.$.getJSON('https://pierreaubert.github.io/spinorama/assets/metadata.json', function (response) {

	const metadata = Object.values(response);
	const fuse = new Fuse(metadata, {
	    matchAllTokens: true,
	    findAllMatches: true,
	    minMatchCharLength: 2,
	    keys: ['brand', 'model', 'type', 'measurements.origin'],
	    treshhold: 0.0,
	    distance: 1,
	    includeScore: true,
	});
	
	$('#searchInput').on('keyup', function () {
	    let resultdiv = $('div.searchresults');
	    let keywords = $(this).val();
	    if (keywords.length === 0) {
		for( let item in response ) {
		    resultdiv.hide();
		}	
		resultdiv.show();
	    } else { 
		let result = fuse.search(keywords);
		if (result.length === 0) {
		    resultdiv.hide();
		} else {
		    for (let item in metadata) {
			let id = (metadata[item].brand + '-' + metadata[item].model).replace(/['. ]/g, '-');
			// console.log('hide:'+id);
			$('#'+id).hide();
		    }
		    let minScore = 1;
		    for (let item in result) {
			if( result[item].score < minScore ) {
			    minScore = result[item].score;
			}
		    }
		    for (let item in result) {
			let id = (result[item].item.brand + '-' + result[item].item.model).replace(/['. ]/g, '-');
			if( (minScore > 0.0) || (result[item].score === 0.0 )) {
			    // console.log('show:'+id+' maxscore:' + minScore+' score:' + result[item].score);
			    $('#'+id).show();
			}
		    }
		    resultdiv.show();
		}
	    }	 
	});
    });
});
