import metadata from './metadata.js'
import { byDate } from './sort.js'
import { getPeq, getID } from './misc.js'

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

export function display () {
  const speakerContainer = document.querySelector('[data-num="0"')
  const fragment1 = new DocumentFragment()
  byDate.forEach(function (value, key) {
    const speaker = metadata[value]
    if ('eq_autoeq' in speaker) {
      fragment1.appendChild(printEQ(value, speaker))
    }
  })
  speakerContainer.appendChild(fragment1)
}
