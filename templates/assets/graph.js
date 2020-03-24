function displayGraph(spec, divName) {
    
    async function run() {
	const config = {
            // default view background color
            // covers the entire view component
            background: "#efefef",
            axis: {
		labelFont: "serif",
		labelFontSize: 14,
		tickWidth: 3,
            },
	};
	
	function patch(spec) {
	    width = window.innerWidth-120;
	    spec.width = width;
	    spec.height = width/2;
	    return spec;
	}
	
	const result = await vegaEmbed("#visGraph", spec, {
            config: config,
            tooltip: { theme: "dark" },
	    patch: patch
	}).then(
	    function(result) {
	      // width = window.innerWidth-300;
		// result.view.width(width);
		// result.view.height(width/2);
		return result;
	    }
	);
	
	// console.log(window.innerWidth);
    }
    run();
}
