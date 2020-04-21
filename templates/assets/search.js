window.$ = window.jQuery;

$(document).ready(function () {

    window.$.getJSON('${site}/assets/metadata.json', function (response) {
	console.log('got json')
	const metadata = Object.values(response)
	console.log('got metadata')
	const fuse = new Fuse(metadata, {
	    isCaseSensitive: false,
	    matchAllTokens: true,
	    findAllMatches: true,
	    minMatchCharLength: 2,
	    keys: ['brand', 'model', 'type', 'measurements.origin', 'shape'],
	    treshhold: 0.1,
	    distance: 2,
	    includeScore: true,
	    useExtendedSearch: true
	})
	
	console.log('starting search')
	
	$('#searchInput').on('keyup', function () {
	    const resultdiv = $('div.searchresults')
	    const keywords = $(this).val()
	    console.log('searching: '+keywords)
	    if (keywords.length === 0) {
		for (const item in metadata) {
		    const id = (metadata[item].brand + '-' + metadata[item].model).replace(/['. ]/g, '-')
		    $('#' + id).show()
		}
		resultdiv.show()
	    } else {
		const result = fuse.search(keywords)
		if (result.length === 0) {
		    resultdiv.hide()
		} else {
		    for (const item in metadata) {
			const id = (metadata[item].brand + '-' + metadata[item].model).replace(/['. ]/g, '-')
			// console.log('hide:'+id);
			$('#' + id).hide()
		    }
		    let minScore = 1
		    for (const item in result) {
			if (result[item].score < minScore) {
			    minScore = result[item].score
			}
		    }
		    for (const item in result) {
			const id = (result[item].item.brand + '-' + result[item].item.model).replace(/['. ]/g, '-')
			if ((minScore > 0.0) || (result[item].score === 0.0)) {
			    // console.log('show:'+id+' maxscore:' + minScore+' score:' + result[item].score);
			    $('#' + id).show()
			}
		    }
		    resultdiv.show()
		}
	    }
	})
    }).fail( function(jqXHR, textStatus, errorThrown) {
	console.log('getJSON request failed! ' + textStatus);
    })
})
