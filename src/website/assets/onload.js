window.onload = () => {
  const navbarBurger = document.querySelector('#navbar-burger')
  const navbarMenu = document.querySelector('.navbar-menu')

  navbarBurger.addEventListener('click', (e) => {
    navbarBurger.classList.toggle('is-active')
    navbarMenu.classList.toggle('is-active')
  })

  const smallSearch = document.querySelector('#smallSearch')
  const searchBar = document.querySelector('#search-bar')

  if (smallSearch && searchBar) {
    smallSearch.addEventListener('click', (e) => {
      searchBar.classList.toggle('is-hidden-mobile')
    })
  }

  const banner = document.querySelector('.banner')
  if (banner) {
    banner.addEventListener('click', (e) => {
      banner.classList.toggle('hidden')
    })
  }

}
