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
            let width = window.innerWidth - 250;
            spec.width = width;
            spec.height = width * 3 / 5;
            return spec;
        }

        const result = await vegaEmbed(divName, spec, {
            config: config,
            tooltip: { theme: "dark" },
            patch: patch
        }).then(
            function (result) {
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

function displayStats(spec, divName) {

    async function run () {
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
            let width = Math.min(window.innerWidth - 180, 800);
            spec.width = width;
            spec.height = width;
            return spec;
        }

        const result = await vegaEmbed(divName, spec, {
            config: config,
            tooltip: { theme: "dark" },
            patch: patch
        }).then(
            function (result) {
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
