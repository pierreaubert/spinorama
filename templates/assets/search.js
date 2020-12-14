Window.$ = window.jQuery;

$(document).ready(function () {

	window.$.getJSON("${site}/assets/metadata.json", function (response) {
		// console.log("got json")
		const metadata = Object.values(response);
		// console.log("got metadata")
		const fuse = new Fuse(metadata, {
			isCaseSensitive: false,
			matchAllTokens: true,
			findAllMatches: true,
			minMatchCharLength: 2,
			keys: ["brand", "model"],
			treshhold: 0.1,
			distance: 2,
			includeScore: true,
			useExtendedSearch: true
		});

		const resultdiv = $("div.searchresults");

		var filter = {
			reviewer: "",
			shape: "",
			power: "",
		};

		function selectDispatch(filter) {
			var keywords = $("#searchInput").val();
			// console.log("keywords: "+keywords)
			if (keywords === "") {
				// console.log("display filter");
				display_filter(resultdiv, metadata, filter);
			} else {
				// console.log("display search");
				var results = fuse.search(keywords);
				display_search(resultdiv, results, filter);
			}
		}

		$("#selectReviewer").on("change", function () {
			// console.log("select reviewer");
			filter["reviewer"] = this.value;
			selectDispatch(filter);
		});

		$("#selectShape").on("change", function () {
			filter["shape"] = this.value;
			selectDispatch(filter);
		});

		$("#selectPower").on("change", function () {
			filter["power"] = this.value;
			selectDispatch(filter);
		});

		$("#searchInput").on("keyup", function () {
			var keywords = $(this).val();
			// console.log("search start "+keywords);
			var results = fuse.search(keywords);
			display_search(resultdiv, results, filter);
		});

		function is_filtered(item, filter) {
			var show = true;
			var default_measurement = item["default_measurement"];
			var origin = item["measurements"][default_measurement]["origin"];
			if (filter.reviewer !== "" && origin !== filter.reviewer) {
				show = false;
			}
			if (filter.power !== "" && item.type !== filter.power) {
				show = false;
			}
			if (filter.shape !== "" && item.shape !== filter.shape) {
				show = false;
			}
			return show;
		}

		function display_filter(resultdiv, meta, filter) {
			// console.log("display filter start");
			for (const item in meta) {
				var show = is_filtered(meta[item], filter);
				const id = (meta[item].brand + "-" + meta[item].model).replace(/['.+& ]/g, "-");
				if (show) {
					$("#" + id).show();
				} else {
					$("#" + id).hide();
				}
			}
			resultdiv.show();
		}

		function display_search(resultdiv, results, filter) {
			// console.log("display search start");
			if (results.length === 0) {
				display_filter(resultdiv, metadata, filter);
				return;
			}
			// hide all
			for (const item in metadata) {
				const id = (metadata[item].brand + "-" + metadata[item].model).replace(/['.+& ]/g, "-");
				$("#" + id).hide();
			}
			// minScore
			let minScore = 1;
			for (const item in results) {
				if (results[item].score < minScore) {
					minScore = results[item].score;
				}
			}
			// console.log("minScore is "+minScore);
			for (var item in results) {
				var show = true;
				var result = results[item];
				var meta = result.item;
				var score = result.score;
				// console.log("evaluating "+meta.brand+" "+meta.model);
				if (show && !is_filtered(meta, filter)) {
					show = false;
				}
				if (show) {
					if (minScore < Math.pow(10, -15) && score >= Math.pow(10, -15)) {
						show = false;
					} else {
						if (score !== minScore) {
							show = false;
						}
					}
				}
				const id = (meta.brand + "-" + meta.model).replace(/[".+& ]/g, "-");
				if (show) {
					$("#" + id).show();
				} else {
					$("#" + id).hide();
				}

			}
			resultdiv.show();
		}

	}).fail(function (jqXHR, textStatus) {
		console.log("getJSON request failed! " + textStatus);
	});

});
