import metadata from './metadata.js'

// sort children
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

function sortMetadata2 (metadata, sorter) {
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
  } else {
    console.log('ERROR: unknown sorter ' + sorter.by)
  }
}

export const byDate = sortMetadata2(metadata, { by: 'date' })
export const byScore = sortMetadata2(metadata, { by: 'score' })
export const byScoreEq = sortMetadata2(metadata, { by: 'scoreEQ' })
export const byScoreWsub = sortMetadata2(metadata, { by: 'scoreWSUB' })
export const byScoreEqWsub = sortMetadata2(metadata, { by: 'scoreEQWSUB' })
export const byPrice = sortMetadata2(metadata, { by: 'price' })

export function sortBy (metadata, sorter) {
  if (sorter.by === 'date') {
    return byDate
  } else if (sorter.by === 'score') {
    return byScore
  } else if (sorter.by === 'scoreEq') {
    return byScoreEq
  } else if (sorter.by === 'scoreWSub') {
    return byScoreWsub
  } else if (sorter.by === 'scoreEqWsub') {
    return byScoreEqWsub
  } else if (sorter.by === 'price') {
    return byPrice
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
  } else {
    console.log('Error sort method is unkown: ' + current_sorter.by)
  }
  return currentMetadata
}
