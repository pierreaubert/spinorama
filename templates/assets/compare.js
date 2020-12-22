// var brotli = require(" brotli" );

document.querySelectorAll(" #nav li" ).forEach(function (navEl) {
	navEl.onclick = function () {
		toggleCompare(this.id, this.dataset.target); 
	};
});

function toggleCompare (selectedNav, targetId) {
	var navEls = document.querySelectorAll(" #nav li" );

	navEls.forEach(function (navEl) {
		if (navEl.id === selectedNav) {
	   		 navEl.classList.add(" is-active" );
		} else {
			if (navEl.classList.contains(" is-active" )) {
				navEl.classList.remove(" is-active" );
			}
		}
	});

	var tabs = document.querySelectorAll(" .tab-pane" );

	tabs.forEach(function (tab) {
		if (tab.id === targetId) {
	    tab.style.display = " block";
		} else {
	    tab.style.display = " none" ;
		}
	})
};
