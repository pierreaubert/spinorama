// import { urlSite, show, hide } from 'misc.js'
// import { sortMetadata } from 'sort.js'

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.text()
  }).then((datajs) => {
  // console.log("got json");
  const metadata = Object.values(JSON.parse(datajs))
  // console.log("got metadata");
  const resultdiv = document.querySelector('div.searchresults')

  const filter = {
    reviewer: '',
    shape: '',
    power: '',
    brand: '',
    quality: ''
  }

  const sorter = {
    by: 'date' // default sort
  }

  function selectDispatch () {
    const keywords = document.querySelector('#searchInput').value
    // console.log("keywords: "+keywords);
    sortMetadata(
      metadata,
      document.querySelector('div.searchresults > div'),
      sorter)

    if (keywords === '') {
      // console.log("display filter");
      display_filter(resultdiv, metadata, filter)
    } else {
      // console.log("display search");
      const fuse = new Fuse(metadata, {
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
      const results = fuse.search(keywords)
      display_search(resultdiv, metadata, results, filter)
    }
    show(resultdiv)
  }

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

  document.querySelector('#sortBy').addEventListener('change', function () {
    sorter.by = this.value
    selectDispatch()
  })

  document.querySelector('#searchInput').addEventListener('keyup', function () {
    selectDispatch()
  })

  function isFiltered (item, filter) {
    let shouldShow = true
    if (filter.reviewer !== '') {
      let found = true
      for (const [name, measurement] of Object.entries(item.measurements)) {
        const origin = measurement.origin.toLowerCase()
        // console.log("debug: name="+name+" origin="+origin+" filter.reviewer="+filter.reviewer);
        if (name.toLowerCase().endsWith(filter.reviewer.toLowerCase()) || origin == filter.reviewer.toLowerCase()) {
          found = false
          break
        }
      }
      if (found) {
        shouldShow = false
      }
    }
    // console.log("debug: name="+name+" post filter reviewer "+shouldShow)
    if (filter.quality !== '') {
      let found = true
      for (const [name, measurement] of Object.entries(item.measurements)) {
        const quality = measurement.quality.toLowerCase()
        // console.log("filter.quality="+filter.quality+" quality="+quality);
        if (filter.quality !== '' && quality == filter.quality.toLowerCase()) {
          found = false
          break
        }
      }
      if (found) {
        shouldShow = false
      }
    }
    // console.log("debug: name="+name+" post quality "+shouldShow)
    if (filter.power !== '' && item.type !== filter.power) {
      shouldShow = false
    }
    // console.log("debug: name="+name+" post power "+shouldShow)
    if (filter.shape !== '' && item.shape !== filter.shape) {
      shouldShow = false
    }
    // console.log("debug: name="+name+" post shape "+shouldShow)
    if (filter.brand !== '' && item.brand.toLowerCase() !== filter.brand.toLowerCase()) {
      shouldShow = false
    }
    // console.log("debug: name="+name+" post brand "+shouldShow)
    return shouldShow
  }

  function display_filter (resultdiv, sorted_meta, filter) {
    // console.log("display filter start #" + sorted_meta.length);
    for (const item in sorted_meta) {
      const shouldShow = isFiltered(sorted_meta[item], filter)
      const id = (sorted_meta[item].brand + '-' + sorted_meta[item].model).replace(/['.+& ]/g, '-')
      if (shouldShow) {
        // console.log(sorted_meta[item].brand + "-"+ sorted_meta[item].model + " is shouldShown");
        show(document.querySelector('#' + id))
      } else {
        // console.log(sorted_meta[item].brand + "-"+ sorted_meta[item].model + " is filtered");
        hide(document.querySelector('#' + id))
      }
    }
  }

  function display_search (resultdiv, sorted_meta, results, filter) {
    // console.log("---------- display search start ----------------");
    const keywords = document.querySelector('#searchInput').value
    if (results.length === 0) {
      display_filter(resultdiv, sorted_meta, filter)
      return
    }
    // hide all
    for (const item in sorted_meta) {
      const id = (sorted_meta[item].brand + '-' + sorted_meta[item].model).replace(/['.+& ]/g, '-')
      hide(document.querySelector('#' + id))
    }
    // minScore
    let minScore = 1
    for (const item in results) {
      if (results[item].score < minScore) {
        minScore = results[item].score
      }
    }
    // console.log("minScore is "+minScore);
    for (const item in results) {
      let shouldShow = true
      const result = results[item]
      const item_meta = result.item
      const score = result.score
      // console.log("evaluating "+item_meta.brand+" "+item_meta.model+" "+score);
      if (!isFiltered(item_meta, filter)) {
        // console.log("filtered out (filter)");
        shouldShow = false
      }
      if (shouldShow) {
        if (minScore < Math.pow(10, -15)) {
          const is_exact = item_meta.model.toLowerCase().includes(keywords.toLowerCase())
          // we have an exact match, only shouldShow other exact matches
          if (score >= Math.pow(10, -15) && !is_exact) {
            // console.log("filtered out (minscore)" + score);
            shouldShow = false
          }
        } else {
          // only partial match
          if (score > minScore * 10) {
            // console.log("filtered out (score="+score+"minscore="+minScore+")");
            shouldShow = false
          }
        }
      }
      const id = (item_meta.brand + '-' + item_meta.model).replace(/['.+& ]/g, '-')
      if (shouldShow) {
        // console.log("show "+item_meta.brand+" "+item_meta.model+" "+score);
        show(document.querySelector('#' + id))
      } else {
        // console.log("hide "+item_meta.brand+" "+item_meta.model+" "+score);
        hide(document.querySelector('#' + id))
      }
    }
  }
})
