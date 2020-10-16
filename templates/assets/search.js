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
	    keys: ['brand', 'model', 'type', 'shape',
		   'measurements.asr.origin', 'measurements.vendor.origin', 'measurements.printeton.origin'
		  ],
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
		    const id = (metadata[item].brand + '-' + metadata[item].model).replace(/['.+& ]/g, '-')
		    $('#' + id).show()
		}
		resultdiv.show()
	    } else {
		const result = fuse.search(keywords)
		if (result.length === 0) {
		    resultdiv.hide()
		} else {
		    for (const item in metadata) {
			const id = (metadata[item].brand + '-' + metadata[item].model).replace(/['.+& ]/g, '-')
			console.log('hide:'+id);
			$('#' + id).hide()
		    }
		    let minScore = 1
		    for (const item in result) {
			if (result[item].score < minScore) {
			    minScore = result[item].score
			}
		    }
		    if (minScore < Math.pow(10,-15)) {
			for (const item in result) {
			    const id = (result[item].item.brand + '-' + result[item].item.model).replace(/['.+& ]/g, '-')
			    if (result[item].score < Math.pow(10,-15)) {
				$('#' + id).show()
				console.log('perfect match:'+id+' minscore:' + minScore+' score:' + result[item].score);
			    } else {
				console.log('skip match:'+id+' minscore:' + minScore+' score:' + result[item].score);
			    }
			}
		    } else {
			for (const item in result) {
			    const id = (result[item].item.brand + '-' + result[item].item.model).replace(/['.+& ]/g, '-')
			    if (result[item].score === minScore) {
				console.log('show:'+id+' minscore:' + minScore+' score:' + result[item].score);
				$('#' + id).show()
			    } else {
				console.log('skip partial match:'+id+' minscore:' + minScore+' score:' + result[item].score);
			    }
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
