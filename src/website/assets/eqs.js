import { urlSite, getPeq, getID } from './misc.js'
import { sortMetadata } from './sort.js'

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.json()
  }).then((datajs) => {
  const speakerContainer = document.querySelector('[data-num="0"')
  const speakerDatabase = Object.values(datajs)

  function getContext (key, value) {
    // console.log(getReviews(value));
    return {
      id: getID(value.brand, value.model),
      brand: value.brand,
      model: value.model,
      autoeq: 'https://raw.githubusercontent.com/pierreaubert/spinorama/develop/datas/eq/' +
                encodeURI(value.brand + ' ' + value.model) +
                '/iir-autoeq.txt',
      preamp_gain: value.eq_autoeq.preamp_gain,
      peq: getPeq(value.eq_autoeq.peq)
    }
  }

  function printEQ (key, value) {
    const source = document.querySelector('#eqsht').innerHTML
    const template = Handlebars.compile(source)
    const context = getContext(key, value)
    const html = template(context)
    const divEQ = document.createElement('div')
    divEQ.setAttribute('class', 'column is-one-third')
    divEQ.setAttribute('id', context.id)
    divEQ.innerHTML = html
    return divEQ
  }

  function display () {
    const fragment1 = new DocumentFragment()
    speakerDatabase.forEach(function (value, key) {
      if ('eq_autoeq' in value) {
        fragment1.appendChild(printEQ(key, value))
      }
    })
    sortMetadata(speakerDatabase, fragment1, { by: 'score' })
    speakerContainer.appendChild(fragment1)
  }

  display()
})
