// https://github.com/BulmaTemplates/bulma-templates/blob/master/js/tabs.js

document.querySelectorAll('#nav li').forEach(function (navEl) {
  navEl.onclick = function () { toggleTab(this.id, this.dataset.target) }
})

function toggleTab (selectedNav, targetId) {
  const navEls = document.querySelectorAll('#nav li')

  navEls.forEach(function (navEl) {
    if (navEl.id === selectedNav) {
      navEl.classList.add('is-active')
    } else {
      if (navEl.classList.contains('is-active')) {
        navEl.classList.remove('is-active')
      }
    }
  })

  const tabs = document.querySelectorAll('.tab-pane')

  tabs.forEach(function (tab) {
    if (tab.id === targetId) {
      tab.style.display = 'block'
    } else {
      tab.style.display = 'none'
    }
  })
};
