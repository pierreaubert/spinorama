window.onload = () => {

    var navbarBurger = document.querySelector('.navbar-burger');
    var navbarMenu = document.querySelector('.navbar-menu');

    navbarBurger.addEventListener('click', (e) => {
        navbarBurger.classList.toggle("is-active");
        navbarMenu.classList.toggle("is-active");
    });

    var smallSearch = document.querySelector('#smallSearch');
    var searchBar = document.querySelector('#search-bar');

    if (smallSearch && searchBar) {
        smallSearch.addEventListener('click', (e) => {
            searchBar.classList.toggle("is-hidden-mobile");
        });
    }

    var banner = document.querySelector('.banner');
    if (banner) {
        banner.addEventListener('click', (e) => {
            banner.classList.toggle("visible");
        });
    }

}
