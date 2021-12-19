window.onload = () => {

    var navbarBurger = document.querySelector('.navbar-burger');
    var navbarMenu = document.querySelector('.navbar-menu');

    navbarBurger.addEventListener('click', (e) => {
        navbarBurger.classList.toggle("is-active");
        navbarMenu.classList.toggle("is-active");
    });

    var banner = document.querySelector('.banner');
    if (banner != null ) {
        banner.addEventListener('click', (e) => {
            banner.classList.toggle("visible");
        });
    }

}
