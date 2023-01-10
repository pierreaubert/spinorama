export function sortMetadata2 (metadata, sorter) {
  const sortChildren2 = ({ container, score }) => {
    const items = [...Array(container.length).keys()]
    items.sort((a, b) => score(b) - score(a))
    return items
  }

  function getDate2 (key) {
    const spk = metadata[key]
    const def = spk.default_measurement
    const msr = spk.measurements[def]
    // comparing ints (works because 20210101 is bigger than 20201010)
    if ('review_published' in msr) {
      const reviewPublished = parseInt(msr.review_published)
      if (!isNaN(reviewPublished)) {
        return reviewPublished
      }
    }
    return 19700101
  }

  function getPrice2 (key) {
    const spk = metadata[key]
    const price = parseInt(spk.price)
    if (!isNaN(price)) {
      return price
    }
    return -1
  }

  function getScore2 (key) {
    const spk = metadata[key]
    const def = spk.default_measurement
    const msr = spk.measurements[def]
    if ('pref_rating' in msr && 'pref_score' in msr.pref_rating) {
      return spk.measurements[def].pref_rating.pref_score
    }
    return -10.0
  }

  function getScoreWsub2 (key) {
    const spk = metadata[key]
    const def = spk.default_measurement
    const msr = spk.measurements[def]
    if ('pref_rating' in msr && 'pref_score_wsub' in msr.pref_rating) {
      return spk.measurements[def].pref_rating.pref_score_wsub
    }
    return -10.0
  }

  function getScoreEq2 (key) {
    const spk = metadata[key]
    const def = spk.default_measurement
    const msr = spk.measurements[def]
    if ('pref_rating_eq' in msr && 'pref_score' in msr.pref_rating_eq) {
      return spk.measurements[def].pref_rating_eq.pref_score
    }
    return -10.0
  }

  function getScoreEqWsub2 (key) {
    const spk = metadata[key]
    const def = spk.default_measurement
    const msr = spk.measurements[def]
    if ('pref_rating_eq' in msr && 'pref_score_wsub' in msr.pref_rating_eq) {
      return spk.measurements[def].pref_rating_eq.pref_score_wsub
    }
    return -10.0
  }

  function getF3v2 (key) {
    const spk = metadata[key]
    const def = spk.default_measurement
    const msr = spk.measurements[def]
    if ('estimates' in msr && 'ref_3dB' in msr.estimates) {
      return -spk.measurements[def].estimates.ref_3dB
    }
    return -1000
  }

  function getF6v2 (key) {
    const spk = metadata[key]
    const def = spk.default_measurement
    const msr = spk.measurements[def]
    if ('estimates' in msr && 'ref_6dB' in msr.estimates) {
      return -spk.measurements[def].estimates.ref_6dB
    }
    return -1000
  }

  function getFlatnessv2 (key) {
    const spk = metadata[key]
    const def = spk.default_measurement
    const msr = spk.measurements[def]
    if ('estimates' in msr && 'ref_band' in msr.estimates) {
      return -spk.measurements[def].estimates.ref_band
    }
    return -1000
  }

  function getSensitivityv2 (key) {
    const spk = metadata[key]
    if ('sensitivity' in spk) {
      return spk.sensitivity
    }
    return 0.0
  }

  if (sorter.by === 'date') {
    return sortChildren2({ container: metadata, score: k => getDate2(k) })
  } else if (sorter.by === 'score') {
    return sortChildren2({ container: metadata, score: k => getScore2(k) })
  } else if (sorter.by === 'scoreEQ') {
    return sortChildren2({ container: metadata, score: k => getScoreEq2(k) })
  } else if (sorter.by === 'scoreWSUB') {
    return sortChildren2({ container: metadata, score: k => getScoreWsub2(k) })
  } else if (sorter.by === 'scoreEQWSUB') {
    return sortChildren2({ container: metadata, score: k => getScoreEqWsub2(k) })
  } else if (sorter.by === 'price') {
    return sortChildren2({ container: metadata, score: k => getPrice2(k) })
  } else if (sorter.by === 'f3') {
    return sortChildren2({ container: metadata, score: k => getF3v2(k) })
  } else if (sorter.by === 'f6') {
    return sortChildren2({ container: metadata, score: k => getF6v2(k) })
  } else if (sorter.by === 'flatness') {
    return sortChildren2({ container: metadata, score: k => getFlatnessv2(k) })
  } else if (sorter.by === 'sensitivity') {
    return sortChildren2({ container: metadata, score: k => getSensitivityv2(k) })
  } else {
    console.log('ERROR: unknown sorter ' + sorter.by)
  }

}

export function sortMetadata (currentMetadata, currentContainer, current_sorter) {
  // console.log("starting sort + sort_by:"+current_sorter.by);
  // TODO build once
  // build a hash map
  const indirectMetadata = {}
  for (const item in currentMetadata) {
    const key = (currentMetadata[item].brand + '-' + currentMetadata[item].model).replace(/['.+& ]/g, '-')
    indirectMetadata[key] = item
    // console.log('adding '+key);
  }

  // sort children
  const sortChildren = ({ container, getScore }) => {
    const items = [...container.children]
    items.sort((a, b) => getScore(b) - getScore(a)).forEach(item => container.appendChild(item))
  }

  function get_price (item) {
    if (item.id in indirectMetadata) {
      const price = parseInt(currentMetadata[indirectMetadata[item.id]].price)
      if (!isNaN(price)) {
        return price
      }
    }
    return -1
  }

  function get_score (item) {
    if (item.id in indirectMetadata) {
      const meta = currentMetadata[indirectMetadata[item.id]]
      const def = meta.default_measurement
      const msr = meta.measurements[def]
      if ('pref_rating' in msr && 'pref_score' in msr.pref_rating) {
        // console.log(item, meta.measurements[def].pref_rating.pref_score);
        return meta.measurements[def].pref_rating.pref_score
      }
    }
    // console.log(item, -10);
    return -10.0
  }

  function get_score_wsub (item) {
    if (item.id in indirectMetadata) {
      const meta = currentMetadata[indirectMetadata[item.id]]
      const def = meta.default_measurement
      const msr = meta.measurements[def]
      if ('pref_rating' in msr && 'pref_score_wsub' in msr.pref_rating) {
        // console.log(item, meta.measurements[def].pref_rating.pref_score);
        return meta.measurements[def].pref_rating.pref_score_wsub
      }
    }
    // console.log(item, -10);
    return -10.0
  }

  function get_score_eq (item) {
    if (item.id in indirectMetadata) {
      const meta = currentMetadata[indirectMetadata[item.id]]
      const def = meta.default_measurement
      const msr = meta.measurements[def]
      if ('pref_rating_eq' in msr && 'pref_score' in msr.pref_rating) {
        return meta.measurements[def].pref_rating_eq.pref_score
      }
    }
    return -10.0
  }

  function get_score_eq_wsub (item) {
    if (item.id in indirectMetadata) {
      const meta = currentMetadata[indirectMetadata[item.id]]
      const def = meta.default_measurement
      const msr = meta.measurements[def]
      if ('pref_rating_eq' in msr && 'pref_score_wsub' in msr.pref_rating) {
        return meta.measurements[def].pref_rating_eq.pref_score_wsub
      }
    }
    return -10.0
  }

  function get_date (item) {
    if (item.id in indirectMetadata) {
      const meta = currentMetadata[indirectMetadata[item.id]]
      const def = meta.default_measurement
      const msr = meta.measurements[def]
      // comparing ints (works because 20210101 is bigger than 20201010)
      if ('review_published' in msr) {
        const review_published = parseInt(msr.review_published)
        if (!isNaN(review_published)) {
          return review_published
        }
      }
    }
    return 19700101
  }

  function get_f3 (item) {
    if (item.id in indirectMetadata) {
      const meta = currentMetadata[indirectMetadata[item.id]]
      const def = meta.default_measurement
      const msr = meta.measurements[def]
      if ('estimates' in msr && 'ref_3dB' in msr.estimates) {
        const f3 = parseFloat(msr.estimates.ref_3dB)
        if (!isNaN(f3)) {
          return -f3
        }
      }
    }
    return -1000
  }

  function get_f6 (item) {
    if (item.id in indirectMetadata) {
      const meta = currentMetadata[indirectMetadata[item.id]]
      const def = meta.default_measurement
      const msr = meta.measurements[def]
      if ('estimates' in msr && 'ref_6dB' in msr.estimates) {
        const f6 = parseFloat(msr.estimates.ref_6dB)
        if (!isNaN(f6)) {
          return -f6
        }
      }
    }
    return -1000
  }

  function get_flatness (item) {
    if (item.id in indirectMetadata) {
      const meta = currentMetadata[indirectMetadata[item.id]]
      const def = meta.default_measurement
      const msr = meta.measurements[def]
      if ('estimates' in msr && 'ref_band' in msr.estimates) {
        const band = parseFloat(msr.estimates.ref_band)
        if (!isNaN(band)) {
          return -band
        }
      }
    }
    return -1000
  }

  function get_sensitivity (item) {
    if (item.id in indirectMetadata) {
      const sensitivity = parseFloat(currentMetadata[indirectMetadata[item.id]].sensitivity)
      if (!isNaN(sensitivity)) {
        return sensitivity
      }
    }
    return 50
  }

  if (current_sorter.by === 'price') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_price(item)
      }
    })
  } else if (current_sorter.by === 'score') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_score(item)
      }
    })
  } else if (current_sorter.by === 'scoreEQ') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_score_eq(item)
      }
    })
  } else if (current_sorter.by === 'scoreWSUB') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_score_wsub(item)
      }
    })
  } else if (current_sorter.by === 'scoreEQWSUB') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_score_eq_wsub(item)
      }
    })
  } else if (current_sorter.by === 'date') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_date(item)
      }
    })
  } else if (current_sorter.by === 'f3') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_f3(item)
      }
    })
  } else if (current_sorter.by === 'f6') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_f6(item)
      }
    })
  } else if (current_sorter.by === 'flatness') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_flatness(item)
      }
    })
  } else if (current_sorter.by === 'sensitivity') {
    sortChildren({
      container: currentContainer,
      getScore: item => {
        return get_sensitivity(item)
      }
    })
  } else {
    console.log('Error sort method is unkown: ' + current_sorter.by)
  }
  return currentMetadata
}
