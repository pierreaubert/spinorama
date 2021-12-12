function displayGraph(spec, divName) {

    async function run() {
        w = window.innerWidth;
        h = window.innerHeight-200;
        if (w/1.414 > h) {
            w =	h*1.414;
        } else {
            h /= 1.414;
        }
        Plotly.newPlot(divName, spec.data, spec.layout);
    }
    run();
}

function displayStats(spec, divName) {

    async function run() {
        spec.layout.width = 1000;
        spec.layout.height = 800;
        Plotly.newPlot(divName, spec.data, spec.layout);
    }
    run();
}
