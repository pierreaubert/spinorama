import { urlSite, show, hide } from './misc.js'
import { sortMetadata } from './sort.js'

let fuse = null

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.json()
  }).then((dataJson) => {
  const metadata = Object.values(dataJson)

  const filter = {
    reviewer: '',
    shape: '',
    power: '',
    brand: '',
    quality: ''
  }

  const sorter = {
    by: 'date'
  }

  function isFiltered (item, filter) {
    let shouldShow = true
    if (filter.reviewer !== undefined && filter.reviewer !== '') {
      let found = true
      for (const [name, measurement] of Object.entries(item.measurements)) {
        const origin = measurement.origin.toLowerCase()
        let name2 = name.toLowerCase()
        name2 = name2.replace('misc-', '')
        console.log('debug: name2=' + name2 + ' origin=' + origin + ' filter.reviewer=' + filter.reviewer)
        if (name2 === filter.reviewer.toLowerCase() || origin === filter.reviewer.toLowerCase()) {
          found = false
          break
        }
      }
      if (found) {
        shouldShow = false
      }
    }
    if (filter.quality !== undefined && filter.quality !== '') {
      let found = true
      for (const [name, measurement] of Object.entries(item.measurements)) {
        const quality = measurement.quality.toLowerCase()
          // console.log('filter.quality=' + filter.quality + ' quality=' + quality)
        if (filter.quality !== '' && quality === filter.quality.toLowerCase()) {
          found = false
          break
        }
      }
      if (found) {
        shouldShow = false
      }
    }
      // console.log('debug: post quality ' + shouldShow)
    if (filter.power !== undefined && filter.power !== '' && item.type !== filter.power) {
      shouldShow = false
    }
      // console.log('debug: post power ' + shouldShow)
    if (filter.shape !== undefined && filter.shape !== '' && item.shape !== filter.shape) {
      shouldShow = false
    }
      // console.log('debug: post shape ' + shouldShow)
    if (filter.brand !== undefined && filter.brand !== '' && item.brand.toLowerCase() !== filter.brand.toLowerCase()) {
      shouldShow = false
    }
      // console.log('debug: post brand ' + shouldShow + 'filter.price=>>>'+filter.price+'<<<')
    if (filter.price !== undefined && filter.price !== '') {
        // console.log('debug: pre price ' + filter.price)
      if (item.price !== '') {
        let price = parseInt(item.price)
        if (item.amount === "pair") {
          price /= 2.0
        }
        switch(filter.price) {
        case "p100":
          if (price>=100) {
            shouldShow = false
          }
          break
        case "p200":
          if (price>=200 || price<=100) {
            shouldShow = false
          }
          break
        case "p300":
          if (price>=300 || price<=200) {
            shouldShow = false
          }
          break
        case "p500":
          if (price>=500 || price<=300) {
            shouldShow = false
          }
          break
        case "p1000":
          if (price>=1000 || price<=500) {
            shouldShow = false
          }
          break
        case "p2000":
          if (price>=2000 || price<=1000) {
            shouldShow = false
          }
          break
        case "p5000":
          if (price>=5000 || price<=2000) {
            shouldShow = false
          }
          break
        case "p5000p":
          if (price<=5000) {
            shouldShow = false
          }
          break
        }
      } else {
        // no known price
        shouldShow = false
      }
        // console.log('debug: post price ' + shouldShow)
    }
    return shouldShow
  }

  function displayFilter (resultdiv, smeta, filter) {
    // console.log('display filter start #' + smeta.length)
    for (const key in smeta) {
      const spk = metadata[key]
      const shouldShow = isFiltered(spk, filter)
      const id = (spk.brand + '-' + spk.model).replace(/['.+& ]/g, '-')
      const elem = document.querySelector('#' + id)
      if (shouldShow) {
        // console.log(spk.brand + '-' + spk.model + ' is shouldShown')
        if (elem) {
          show(elem)
        }
      } else {
        // console.log(spk.brand + '-' + spk.model + ' is filtered')
        if (elem) {
          hide(elem)
        }
      }
    }
  }

  function displaySearch (resultdiv, smeta, results, filter) {
    // console.log('---------- display search start ----------------')
    const keywords = document.querySelector('#searchInput').value
    if (results.length === 0) {
      displayFilter(resultdiv, smeta, filter)
      return
    }
    // hide all
    for (const key in smeta) {
      const spk = metadata[key]
      const id = (spk.brand + '-' + spk.model).replace(/['.+& ]/g, '-')
        // console.log('generated id is ' + id)
      const elem = document.querySelector('#' + id)
      if (elem) {
        hide(elem)
      }
    }
    // minScore
    let minScore = 1
    for (const spk in results) {
      if (results[spk].score < minScore) {
        minScore = results[spk].score
      }
    }
      // console.log('minScore is ' + minScore)
    for (const spk in results) {
      let shouldShow = true
      const result = results[spk]
      const imeta = result.item
      const score = result.score
      if (!isFiltered(imeta, filter)) {
        // console.log('filtered out (filter)')
        shouldShow = false
      }
      if (shouldShow) {
        if (minScore < Math.pow(10, -15)) {
          const isExact = imeta.model.toLowerCase().includes(keywords.toLowerCase())
            // console.log('isExact '+isExact+' model'+imeta.model.toLowerCase()+' keywords '+keywords.toLowerCase())
          // we have an exact match, only shouldShow other exact matches
          if (score >= Math.pow(10, -15) && !isExact) {
            // console.log('filtered out (minscore)' + score)
            shouldShow = false
          }
        } else {
        // only partial match
          if (score > minScore * 10) {
            // console.log('filtered out (score=' + score + 'minscore=' + minScore + ')')
            shouldShow = false
          }
        }
      }
      const id = (imeta.brand + '-' + imeta.model).replace(/['.+& ]/g, '-')
      const elem = document.querySelector('#' + id)
      if (shouldShow) {
        // console.log('show ' + imeta.brand + ' ' + imeta.model + ' ' + score)
        if (elem) {
          show(elem)
        }
      } else {
          // console.log('hide ' + imeta.brand + ' ' + imeta.model + ' ' + score)
        if (elem) {
          hide(elem)
        }
      }
    }
  }

  function selectDispatch () {
    const resultdiv = document.querySelector('div.searchresults')
    const keywords = document.querySelector('#searchInput').value
      // console.log('keywords: ' + keywords)

    // need to sort here
    sortMetadata(
      metadata,
      document.querySelector('div.searchresults > div'),
      sorter)

    //
    if (keywords === '') {
      // console.log('display filter')
      displayFilter(resultdiv, metadata, filter)
    } else {
      // console.log('display search')
      const results = fuse.search(keywords)
      displaySearch(resultdiv, metadata, results, filter)
    }
    show(resultdiv)
  }

  function search () {
    fuse = new Fuse(metadata, {
      isCaseSensitive: false,
      matchAllTokens: true,
      findAllMatches: true,
      minMatchCharLength: 2,
      keys: ['brand', 'model'],
      treshhold: 0.5,
      distance: 4,
      includeScore: true,
      useExatendedSearch: true
    })

    document.querySelector('#selectReviewer').addEventListener('change', function () {
      filter.reviewer = this.value
      selectDispatch()
    })

    document.querySelector('#selectQuality').addEventListener('change', function () {
      filter.quality = this.value
      selectDispatch()
    })

    document.querySelector('#selectShape').addEventListener('change', function () {
      filter.shape = this.value
      selectDispatch()
    })

    document.querySelector('#selectPower').addEventListener('change', function () {
      filter.power = this.value
      selectDispatch()
    })

    document.querySelector('#selectBrand').addEventListener('change', function () {
      filter.brand = this.value
      selectDispatch()
    })

    document.querySelector('#selectPrice').addEventListener('change', function () {
      filter.price = this.value
      selectDispatch()
    })

    document.querySelector('#sortBy').addEventListener('change', function () {
      sorter.by = this.value
      selectDispatch()
    })

    document.querySelector('#searchInput').addEventListener('keyup', function () {
      selectDispatch()
    })
  }

  search()
}).catch(err => console.log(err.message))
