const knownMeasurements = [
    'CEA2034',
    'CEA2034 with splitted views',
    'On Axis',
    'Estimated In-Room Response',
    'Early Reflections',
    'Horizontal Reflections',
    'Vertical Reflections',
    'SPL Horizontal',
    'SPL Horizontal Normalized',
    'SPL Vertical',
    'SPL Vertical Normalized',
    'SPL Horizontal Contour',
    'SPL Horizontal Contour Normalized',
    'SPL Vertical Contour',
    'SPL Vertical Contour Normalized',
    'SPL Horizontal Radar',
    'SPL Vertical Radar',
];

const colors = [
    "#5c77a5",
    "#dc842a",
    "#c85857",
    "#89b5b1",
    "#71a152",
    "#bab0ac",
    "#e15759",
    "#b07aa1",
    "#76b7b2",
    "#ff9da7",
]

const uniformColors = {
    // regression
    "Linear Regression": colors[0],
    "Band ±1.5dB": colors[1],
    "Band ±3dB": colors[1],
    // PIR
    "Estimated In-Room Response": colors[0],
    // spin
    "On Axis": colors[0],
    "Listening Window": colors[1],
    "Early Reflections": colors[2],
    "Sound Power": colors[3],
    "Early Reflections DI": colors[4],
    "Sound Power DI": colors[5],
    // reflections
    "Ceiling Bounce": colors[1],
    "Floor Bounce": colors[2],
    "Front Wall Bounce": colors[3],
    "Rear Wall Bounce": colors[4],
    "Side Wall Bounce": colors[5],
    //
    "Ceiling Reflection": colors[1],
    "Floor Reflection": colors[2],
    //
    "Front": colors[1],
    "Rear": colors[2],
    "Side": colors[3],
    //
    "Total Early Reflection": colors[7],
    "Total Horizontal Reflection": colors[8],
    "Total Vertical Reflection": colors[9],
    // SPL
    "10°": colors[1],
    "20°": colors[2],
    "30°": colors[3],
    "40°": colors[4],
    "50°": colors[5],
    "60°": colors[6],
    "70°": colors[7],
    // Radars
    "500 Hz": colors[1],
    "1000 Hz": colors[2],
    "2000 Hz": colors[3],
    "10000 Hz": colors[4],
    "15000 Hz": colors[5],
};

const urlSite = '${site}'+'/';
const urlCompare = urlSite + 'compare.html?';

fetch(urlSite+'assets/metadata.json').then(
    function(response) {
	return response.text();
    }).then( (datajs) => {

	const speakerDatabase = Object.values(JSON.parse(datajs));
	let metadata = {};
	let nbSpeakers = 2;

	const queryString = window.location.search;
	const urlParams = new URLSearchParams(queryString);

	var plotContainer = document.querySelector('[data-num="0"');
	var plotSingleContainer = plotContainer.querySelector('.plotSingle');
	var plotDouble0Container = plotContainer.querySelector('.plotDouble0');
	var plotDouble1Container = plotContainer.querySelector('.plotDouble1');
	var formContainer = plotContainer.querySelector('.plotForm');
	var graphsSelector = formContainer.querySelector('.graph');

        let windowWidth = window.innerWidth;
        let windowHeight = window.innerHeight;

	function getAllSpeakers() {
	    let speakers = [];
	    speakerDatabase.forEach( function(value, key) {
		var speaker = value.brand+' '+value.model;
		speakers.push(speaker);
		metadata[speaker] = value;
	    });
	    return speakers.sort();
	}

	function processOrigin(origin) {
	    if (origin.includes('Vendors-')) {
		return origin.slice(8);
	    }
	    return origin;
	}

	function processGraph(name) {
	    if (name.includes('CEA2034')) {
		return 'CEA2034';
	    }
	    return name;
	}

	function getOrigin(speaker, origin, version) {
	    // console.log('getOrigin ' + speaker + ' origin=' + origin + ' version='+version);
	    if (origin == null || origin == '') {
		default_measurement = metadata[speaker].default_measurement;
		default_origin = metadata[speaker].measurements[default_measurement].origin;
		// console.log('getOrigin default=' + default_origin );
		return processOrigin(default_origin);
	    }
	    return processOrigin(origin);
	}

	function getVersion(speaker, origin, version) {
	    if (version == null || version == '') {
		default_version = metadata[speaker].default_measurement;
		return default_version;
	    }
	    return version;
	}

	function getSpeakerData(graph, speaker, origin, version) {
	    // console.log('getSpeakerData ' + graph + ' speaker=' + speaker + ' origin=' + origin + ' version='+version);
	    var url =
		urlSite +
		speaker + '/' +
		getOrigin(speaker, origin, version) + '/' +
		getVersion(speaker, origin, version) +'/' +
		processGraph(graph)+'.json.zip';
	    // console.log('fetching url='+url);
	    const spec = downloadZip(url).then( function(spec) {
		// console.log('parsing url='+url);
		return JSON.parse(spec);
	    }).catch( (error) => {
		console.log('getSpeaker data 404 '+error);
		return null;
	    });
	    return spec;
	}

	function setLayoutAndDataPrimary(spin) {
	    var layout = null;
	    var datas = null;
	    // console.log('layout and data: '+spin.length);
	    if (spin[0] != null && spin[1] != null ) {
		layout = spin[0].layout;
		datas = spin[0].data.concat(spin[1].data);
	    } else if (spin[0] != null ) {
		layout = spin[0].layout;
		datas = spin[0].data;
	    } else if (spin[1] != null ) {
		layout = spin[1].layout;
		datas = spin[1].data;
	    }
	    if (layout != null && datas != null ) {
		layout.width = windowWidth;
		layout.height = Math.min(windowHeight, windowWidth*0.7+140);
		layout.title = null;
		layout.margin = {
		    'l': 15,
		    'r': 15,
		    't': 30,
		    'b': 50,
		};
                layout.legend = {
                    'orientation': 'h',
                    'y': -0.2,
                    'x': 0,
                    'xanchor': 'bottom',
                    'yanchor': 'left',
                };
                layout.xaxis.autotick = false;
		plotSingleContainer.style.display = "block";
		plotDouble0Container.style.display = "none";
		plotDouble1Container.style.display = "none";
		Plotly.newPlot('plotSingle', datas, layout, {responsive: true});
	    } else {
		// should be a pop up
		console.log('No graph available');
	    }
	}

	function setCEA2034(speaker_names, speaker_graphs) {
	    // console.log('got ' + speaker_graphs.length +' graphs');
	    for (let i = 0 ; i<speaker_graphs.length ; i++ ) {
		if (speaker_graphs[i] != null ) {
		    // console.log('adding graph '+ i);
		    for (var trace in speaker_graphs[i].data) {
			// speaker_graphs[i].data[trace]["legendgroup"] = "speaker"+i;
                        // speaker_graphs[i].data[trace]["legendgrouptitle"] = {"text": speaker_names[i]};
			if ( i % 2 == 1 ) {
			    speaker_graphs[i].data[trace].line = {"dash": "dashdot"};
			}
		    }
		}
	    }
	    setLayoutAndDataPrimary(speaker_graphs);
	}

	function setCEA2034Split(speaker_names, speaker_graphs) {
	    // console.log('got ' + speaker_graphs.length +' graphs');
	    for (let i = 0 ; i<speaker_graphs.length ; i++ ) {
		if (speaker_graphs[i] != null ) {
		    // console.log('adding graph '+ i);
		    for (var trace in speaker_graphs[i].data) {
			speaker_graphs[i].data[trace]["legendgroup"] = "speaker"+i;
			speaker_graphs[i].data[trace]["legendgrouptitle"] = {"text": speaker_names[i]};
			if ( i % 2 == 1 ) {
			    speaker_graphs[i].data[trace].line = {"dash": "dashdot"};
			}
		    }
		}
	    }
	    var layout = null;
	    var datas = null;

	    if (speaker_graphs[0] != null && speaker_graphs[1] != null ) {
		layout = speaker_graphs[0].layout;
		datas = speaker_graphs[0].data.concat(speaker_graphs[1].data);

		layout.width = windowWidth;
		layout.height = Math.min(windowHeight, windowWidth*0.7-240);
		layout.title = null;
		layout.margin = {
		    'l': 0,
		    'r': 0,
		    't': 30,
		    'b': 50,
		};
                layout.legend = {
                    'orientation': 'h',
                    'y': -0.2,
                    'x': 0,
                    'xanchor': 'bottom',
                    'yanchor': 'left',
		    'itemclick': "toggleothers",
                };

		plotSingleContainer.style.display = "block";
		Plotly.newPlot('plotSingle', datas, layout, {responsive: true});

		var deltas = [];
		for (var g0 in speaker_graphs[0].data ) {
		    const name0 = speaker_graphs[0].data[g0].name;
		    const deltas_x = speaker_graphs[0].data[g0].x;
		    for (var g1 in speaker_graphs[1].data ) {
			if (name0 === speaker_graphs[1].data[g1].name ) {
			    var deltas_y = [];
			    for (let i in speaker_graphs[0].data[g0].y) {
				deltas_y[i] = speaker_graphs[0].data[g0].y[i] - speaker_graphs[1].data[g1].y[i];
			    }
			    deltas.push({
				"x": deltas_x,
				"y": deltas_y,
				"type": 'scatter',
				"name": name0,
				//"legendgroup": "differences",
				//"legendgrouptitle": {
				//    "text": 'Differences',
				//},
				"marker": {
                                    "color": uniformColors[name0],
                                },
			    });
			}
		    }
		}
		// console.log(deltas.length);
		// deltas.forEach( (data) => console.log(data.name) );

		layout2 = JSON.parse(JSON.stringify(layout));
		layout2.height = 340;
		layout2.yaxis = {
		    "title": "Delta SPL (dB)",
		    "range": [-5, 5],
		    "dtick": 1,
		};
		layout2.showlegend = true;
		layout2.legend= layout.legend;
		layout2.margin= layout.margin;
		plotDouble0Container.style.display = "block";
		Plotly.newPlot('plotDouble0', deltas, layout2, {responsive: true});
		plotDouble1Container.style.display = "none";
	    } else {
		setLayoutAndDataPrimary(speaker_graphs);
	    }
	}

	function setGraph(speaker_names, speaker_graphs) {
	    // console.log('got ' + speaker_names.length + ' names and '+ speaker_graphs.length +' graphs');
	    for (let i = 0 ; i<speaker_graphs.length ; i++ ) {
		if (speaker_graphs[i] != null ) {
		    // console.log('adding graph '+ i);
		    for (var trace in speaker_graphs[i].data) {
			speaker_graphs[i].data[trace]["legendgroup"] = "speaker"+i;
			speaker_graphs[i].data[trace]["legendgrouptitle"] = {"text": speaker_names[i]};
			if ( i % 2 == 1 ) {
			    speaker_graphs[i].data[trace].line = {"dash": "dashdot"};
			}
		    }
		}
	    }
	    setLayoutAndDataPrimary(speaker_graphs);
	}

	function setContour(speaker_names, speaker_graphs) {
	    plotSingleContainer.style.display = "none";
	    plotDouble0Container.style.display = "block";
	    plotDouble1Container.style.display = "block";
	    for (let i = 0 ; i<speaker_graphs.length ; i++ ) {
		if (speaker_graphs[i] != null ) {
		    for (let j in speaker_graphs[i].data) {
			speaker_graphs[i].data[j].legendgroup = "speaker"+i;
			speaker_graphs[i].data[j].legendgrouptitle = {"text": speaker_names[i]};
		    }
		    var datas = speaker_graphs[i].data;
		    var layout = speaker_graphs[i].layout;
		    Plotly.newPlot('plotDouble'+i, datas, layout, {responsive: true});
		}
	    }
	}

	function plot(measurement, speakers_name, speakers_graph) {
	    // console.log('plot: ' + speakers_name.length + ' names and ' + speakers_graph.length + ' graphs');
	    async function run() {
		Promise.all(speakers_graph).then( (graphs) => {
		    // console.log('plot: resolved ' + graphs.length + ' graphs');
		    if (measurement === 'CEA2034' ) {
			return setCEA2034(speakers_name, graphs);
		    } else if( measurement === 'CEA2034 with splitted views') {
			return setCEA2034Split(speakers_name, graphs);
		    } else if( measurement === 'On Axis' ||
			       measurement === 'Estimated In-Room Response' ||
			       measurement === 'Early Reflections' ||
			       measurement === 'SPL Horizontal' ||
			       measurement === 'SPL Vertical' ||
			       measurement === 'SPL Horizontal Normalized' ||
			       measurement === 'SPL Vertical Normalized' ||
			       measurement === 'Horizontal Reflections' ||
			       measurement === 'Vertical Reflections' ||
			       measurement === 'SPL Horizontal Radar' ||
			       measurement === 'SPL Vertical Radar' ) {
			return setGraph(speakers_name, graphs);
		    } else if( measurement === 'SPL Horizontal Contour' ||
			       measurement === 'SPL Vertical Contour' ||
			       measurement === 'SPL Horizontal Contour Normalized' ||
			       measurement === 'SPL Vertical Contour Normalized' ) {
			return setContour(speakers_name, graphs);
		    } // todo add multi view
		    return null;
		});
	    }
	    run();
	}

	function assignOptions(textArray, selector, textSelected) {
	    // console.log('assignOptions: selected = '+textSelected);
	    // textArray.forEach( item => console.log('assignOptions: '+item));
	    while (selector.firstChild) {
		selector.firstChild.remove();
	    }
	    for (var i = 0; i < textArray.length;  i++) {
		var currentOption = document.createElement('option');
		currentOption.text = textArray[i];
		if (textArray[i] == textSelected) {	currentOption.selected = true; }
		if (textArray.length == 1) {currentOption.disabled = true;}
		selector.appendChild(currentOption);
	    }
	}

	function buildInitSpeakers(speakers, count) {
	    var list = [];
	    for (let pos = 0 ; pos < count ; pos++ ) {
		if (urlParams.has('speaker'+pos)) {
		    list[pos] = urlParams.get('speaker'+pos);
		    continue;
		}
		list[pos] = speakers[Math.floor(Math.random() * speakers.length)];
	    }
	    return list;
	}

	var speakers = getAllSpeakers();
	var initSpeakers = buildInitSpeakers(speakers, nbSpeakers);

	var speakersSelector = [];
	var originsSelector = [];
	var versionsSelector = [];
	for (let pos = 0 ; pos < nbSpeakers ; pos++ ) {
	    var tpos = pos.toString();
	    speakersSelector[pos] = formContainer.querySelector('.speaker'+tpos);
	    originsSelector[pos]  = formContainer.querySelector('.origin' +tpos);
	    versionsSelector[pos] = formContainer.querySelector('.version'+tpos);
	}

	for (let pos = 0 ; pos < nbSpeakers ; pos++ ) {
	    assignOptions(speakers, speakersSelector[pos], initSpeakers[pos]);
	}
	assignOptions(knownMeasurements, graphsSelector, knownMeasurements[0]);

	function updateVersion(speaker, selector, origin, value) {
	    // update possible version(s) for matching speaker and origin
	    // console.log('update version for '+speaker+' origin='+origin);
	    var versions = Object.keys(metadata[speaker].measurements);
	    var matches = [];
	    versions.forEach( (val) => {
		var current = metadata[speaker].measurements[val];
		if ( current.origin == origin || origin == '' || origin == null) {
		    matches.push(val);
		}
	    });
	    if (metadata[speaker].eq != null) {
		var matchesEQ = [];
		for (let key in matches) {
		    matchesEQ.push(matches[key]+'_eq');
		}
		matches = matches.concat(matchesEQ);
	    }
	    if (value != null ) {
		assignOptions(matches, selector, value);
	    } else {
		assignOptions(matches, selector, selector.value);
	    }
	}

	function updateOrigin(speaker, originSelector, versionSelector, origin, version) {
	    // console.log('updateOrigin for '+speaker+' with origin '+origin);
	    const measurements = Object.keys(metadata[speaker].measurements);
	    var origins = new Set();
	    for (let key in measurements) {
		origins.add(metadata[speaker].measurements[measurements[key]].origin);
	    }
	    const [first] = origins;
	    // console.log('updateOrigin found this possible origins: '+origins.size+' first='+first);
	    // origins.forEach(item => console.log('updateOrigin: ' + item));
	    if (origin != null) {
		assignOptions(Array.from(origins), originSelector, origin);
	    }  else {
		assignOptions(Array.from(origins), originSelector, first);
	    }
	    updateVersion(speaker, versionSelector, originSelector.value, version);
	}

	function updateSpeakers() {
	    var names = [];
	    var graphs = [];
	    for (let i = 0 ; i < nbSpeakers ; i++ ) {
		graphs[i] = getSpeakerData(
		    graphsSelector.value,
		    speakersSelector[i].value,
		    originsSelector[i].value,
		    versionsSelector[i].value
		);
		names[i] = speakersSelector[i].value;
	    }
	    plot(graphsSelector.value, names, graphs);
	}

	function updateSpeakerPos(pos) {
	    // console.log('updateSpeakerPos('+pos+')');
	    updateOrigin(speakersSelector[pos].value, originsSelector[pos], versionsSelector[pos]);
	    urlParams.set('speaker'+pos, speakersSelector[pos].value);
	    history.pushState(
                {page: 1},
                'Compare speakers',
                urlCompare+urlParams.toString()
            );
	    updateSpeakers();
	}

	function updateVersionPos(pos) {
	    // console.log('updateVersionsPos('+pos+')');
	    updateVersion(
		speakersSelector[pos].value,
		versionsSelector[pos],
		originsSelector[pos].value,
		versionsSelector[pos].value
	    );
	    updateSpeakers();
	    urlParams.set('version'+pos, versionsSelector[pos].value);
	    history.pushState(
                {page: 1},
                'Compare speakers',
                urlCompare+urlParams.toString()
            );
	}

	function updateOriginPos(pos) {
	    // console.log('updateOriginPos('+pos+')');
	    updateOrigin(speakersSelector[pos].value, originsSelector[pos], versionsSelector[pos], originsSelector[pos].value);
	    urlParams.set('origin'+pos, originsSelector[pos].value);
	    history.pushState(
                {page: 1},
                'Compare speakers',
                urlCompare+urlParams.toString()
            );
	    updateSpeakers();
	}

	// initial setup
	const cea2034 = knownMeasurements[0];
	let initDatas = [];
	for (let pos = 0 ; pos < nbSpeakers ; pos++ ) {
	    updateOrigin(
		initSpeakers[pos],
		originsSelector[pos],
		versionsSelector[pos],
		urlParams.get('origin'+pos),
		urlParams.get('version'+pos)
	    );
	    // console.log('DEBUG: '+originsSelector[pos].options[0])
	    initDatas[pos] = getSpeakerData(cea2034, initSpeakers[pos], null, null);
	}

	// add listeners
	graphsSelector.addEventListener('change', updateSpeakers, false);

	for (let pos = 0 ; pos < nbSpeakers ; pos++ ) {
	    speakersSelector[pos].addEventListener('change', (event) => {return updateSpeakerPos(pos)}, false);
	    originsSelector[pos].addEventListener('change',  (event) => {return updateOriginPos(pos)},  false);
	    versionsSelector[pos].addEventListener('change', (event) => {return updateVersionPos(pos)}, false);
	}

	plot(cea2034, initSpeakers, initDatas );

    });
