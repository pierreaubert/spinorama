function displayGraph(spec, divName) {

    async function run() {
        w = window.innerWidth;
        h = window.innerHeight;
        console.log('IN w='+w+' h='+h);
        if (w < h) {
            h =	Math.min(w/1.414+200, h);
        } else {
            w = h/1.414;
        }
        console.log('OUT w='+w+' h='+h);
        spec.layout.width = w;
        spec.layout.height = h;
        if (w > 640) {
	    spec.layout.margin = {
	        'l': 15,
	        'r': 15,
	        't': 50,
	        'b': 50,
	    };
            spec.layout.legend = {
                'orientation': 'h',
                'y': -0.2,
                'x': 0,
                'xanchor': 'bottom',
                'yanchor': 'left',
            };
        } else {
            if (w<h) {
                spec.layout.yaxis.visible = false;
                spec.layout.yaxis2.visible = false;
	        spec.layout.margin = {
	            'l': 0,
	            'r': 0,
	            't': 100,
	            'b': 100,
	        };
                spec.layout.legend = {
                    'orientation': 'h',
                    'y': -0.4,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'left',
                };
                var title = spec.layout.title.text;
                var pos = title.indexOf('measured');
                spec.layout.title = {
                    'text': title.slice(0, pos),
                    'orientation': 'h',
                    'y': 0.85,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'left',
                };
            } else {
                spec.layout.xaxis.visible = false;
	        spec.layout.margin = {
	            'l': 0,
	            'r': 0,
	            't': 0,
	            'b': 0,
	        };
                spec.layout.legend = {
                    'orientation': 'v',
                };
                var title = spec.layout.title.text;
                var pos = title.indexOf('measured');
                spec.layout.title = {
                    'text': title.slice(0, pos),
                    'orientation': 'v',
                };
            }
        }
        Plotly.newPlot(divName, spec.data, spec.layout);
    }
    run();
}

//function displayStats(spec, divName) {
//
//    async function run() {
//        spec.layout.width = window.innerWidth;
//        spec.layout.height = window.innerHeight;
//        Plotly.newPlot(divName, spec.data, spec.layout);
//    }
//    run();
//}
