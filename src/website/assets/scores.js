// import { urlSite, getID, getPicture, getLoading, getDecoding, getField, getReviews } from 'misc.js'
// import { sortMetadata } from 'sort.js'

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.json()
  }).then((datajs) => {
  const speakerContainer = document.querySelector('[data-num="0"')
  const speakerDatabase = Object.values(datajs)

  function getSpider (brand, model) {
    // console.log(brand + model);
    return encodeURI(brand + ' ' + model + '/spider.jpg')
  }

  function getContext (key, value) {
    // console.log(getReviews(value));
    const scores = getField(value, 'pref_rating')
    scores.pref_score = parseFloat(scores.pref_score).toFixed(1)
    scores.pref_score_wsub = parseFloat(scores.pref_score_wsub).toFixed(1)
    const scoresEQ = getField(value, 'pref_rating_eq')
    scoresEQ.pref_score = parseFloat(scoresEQ.pref_score).toFixed(1)
    scoresEQ.pref_score_wsub = parseFloat(scoresEQ.pref_score_wsub).toFixed(1)
    return {
      id: getID(value.brand, value.model),
      brand: value.brand,
      model: value.model,
      sensitivity: value.sensitivity,
      estimates: getField(value, 'estimates'),
      estimates_eq: getField(value, 'estimates_eq'),
      scores: scores,
      scoresEQ: scoresEQ,
      reviews: getReviews(value),
      img: {
        // avif: getPicture(value.brand, value.model, "avif"),
        webp: getPicture(value.brand, value.model, 'webp'),
        jpg: getPicture(value.brand, value.model, 'jpg'),
        loading: getLoading(key),
        decoding: getDecoding(key)
      },
      spider: getSpider(value.brand, value.model)
    }
  }

  function printScore (key, value) {
    const source = document.querySelector('#scoresht').innerHTML
    const template = Handlebars.compile(source)
    const context = getContext(key, value)
    const html = template(context)
    const divScore = document.createElement('div')
    divScore.setAttribute('id', context.id)
    divScore.setAttribute('class', 'column py-0 is-12 is-vertical')
    divScore.innerHTML = html
    return divScore
  }

  function display () {
    const fragment1 = new DocumentFragment()
    speakerDatabase.forEach(function (value, key) {
      fragment1.appendChild(printScore(key, value))
    })
    sortMetadata(speakerDatabase, fragment1, { by: 'score' })
    speakerContainer.appendChild(fragment1)
  }

  display()
})
