// import Fuse from 'fuse.js';

window.$ = window.jQuery;

function display_speaker(speaker) {
    let s_href = speaker.speaker + '/'+ speaker.speaker.origin + '/index.html'
    let s_img  = 'metadata/' + speaker.speaker + '.jpg'
    let s_name = speaker.brand + ' ' + speaker.model 
    let content = '	    <div class="column is-one-third">		<div class="card large">		  <div class="card-image">		    <figure class="image"><img src="' + s_img + '" alt="Spinorama"/></figure>		  </div>		  <div class="card-content">		    <div class="media">                      <div class="content">			<div class="content">' + s_name + '</div>	              </div>	            </div>		    <div class="media">			-3dB at ' + speaker.estimates[1] + 'Hz<br/>			-6dB at ' + speaker.estimates[2] + 'Hz<br/>			&plusmn;' + speaker.estimates[3] + 'dB ~ 80-20kHz		  </div>                  <div class="right">		    <label class="checkbox is-large"><input type="checkbox"/></label>	          </div>		</div>             </div>';
    return content
}

$(document).ready(function () {

    window.$.getJSON('http://192.168.1.104:8888/docs/assets/metadata.json', function (response) {
	
	const fuse = new Fuse(response, {
	    matchAllTokens: true,
	    minMatchCharLength: 2,
	    includeMatches: true,
	    keys: ['brand', 'model'],
	    // id: 'speaker',
	    tags: ['type']
	});
	
	$('#searchInput').on('keyup', function () {
	    let resultdiv = $('div.searchresults');
	    let keywords = $(this).val();
	    if (keywords.length === 0) {
		resultdiv.empty();
		for( let item in response ) {
		    resultdiv.append(display_speaker(response[item]));
		}	
		resultdiv.show();
	    } else { 
		let result = fuse.search(keywords);
		if (result.length === 0) {
		    resultdiv.hide();
		} else {
		    resultdiv.empty();
		    for (let item in result) {
			let name = result[item].item.speaker
			let match = response.find(response => response.speaker === name);
			let searchitem = display_speaker(match);
			resultdiv.append(searchitem);
		    }	
		    resultdiv.show();
		}
	    }	 
	});
    });
});
