export const urlSite = '${site}' + '/'

// hide an element
export const hide = (elem) => {
  elem.classList.add('hidden')
}

// show an element
export const show = (elem) => {
  elem.classList.remove('hidden')
}

// toggle the element visibility
export const toggle = (elem) => {
  elem.classList.toggle('hidden')
}

export function toggleId (id) {
  const elem = document.querySelector(id)
  if (elem && elem.classList) {
    elem.classList.toggle('hidden')
  }
}

function getEQType (type) {
  let val = 'unknown'
  switch (type) {
    case 0:
      val = 'LP'
      break
    case 1:
      val = 'HP'
      break
    case 2:
      val = 'BP'
      break
    case 3:
      val = 'PK'
      break
    case 4:
      val = 'NO'
      break
    case 5:
      val = 'LS'
      break
    case 6:
      val = 'HS'
      break
  }
  return val
}

export function getPeq (peq) {
  const peqPrint = []
  peq.forEach((eq) => {
    peqPrint.push({
      freq: eq.freq,
      dbGain: eq.dbGain,
      Q: eq.Q,
      type: getEQType(eq.type)
    })
  })
  return peqPrint
}

export function getPicture (brand, model, suffix) {
  return encodeURI('pictures/' + brand + ' ' + model + '.' + suffix)
}

export function removeVendors (str) {
  return str.replace('Vendors-', '')
}

export function getID (brand, model) {
  return (brand + ' ' + model).replace(/['.+& ]/g, '-')
}

export function getField (value, field, version) {
  let fields = {}
  if (value.measurements && value.measurements[version]) {
    const measurement = value.measurements[version]
    if (measurement.hasOwnProperty(field)) {
      fields = measurement[field]
    }
  }
  return fields
}

export function getReviews (value) {
  const reviews = []
  for (const version in value.measurements) {
    const measurement = value.measurements[version]
    let origin = measurement.origin
    const url = 'speakers/' + value.brand + ' ' + value.model + '/' + removeVendors(origin) + '/index_' + version + '.html'
    if (origin === 'Misc') {
      origin = version.replace('misc-', '')
    } else {
      origin = origin.replace('Vendors-', '')
    }
    if (origin === 'ErinsAudioCorner') {
      origin = 'EAC'
    } else if (origin === 'Princeton') {
      origin = '3D3A'
    } else if (origin === 'napilopez') {
      origin = 'NPZ'
    } else if (origin === 'speakerdata2034') {
      origin = 'SPD'
    }
    origin = origin.charAt(0).toUpperCase() + origin.slice(1)
    reviews.push({
      url: encodeURI(url),
      origin: origin,
      version: version,
      scores: getField(value, 'pref_rating', version),
      scoresEq: getField(value, 'pref_rating_eq', version),
      estimates: getField(value, 'estimates', version),
      estimatesEq: getField(value, 'estimates_eq', version)
    })
  }
  return {
    reviews: reviews
  }
}

export function getScore (value, def) {
  if (def) {
    def = value.default_measurement
  }
  let score = 0.0
  let lfx = 0.0
  let flatness = 0.0
  let smoothness = 0.0
  let scoreScaled = 0.0
  let lfxScaled = 0.0
  let flatnessScaled = 0.0
  let smoothnessScaled = 0.0
  if (value.measurements &&
        value.measurements[def].pref_rating) {
    const measurement = value.measurements[def]
    const pref = measurement.pref_rating
    score = pref.pref_score
    if (pref.lfx_hz) {
      lfx = pref.lfx_hz
    }
    smoothness = pref.sm_pred_in_room
    const prefScaled = measurement.scaled_pref_rating
    scoreScaled = prefScaled.scaled_pref_score
    if (prefScaled.scaled_lfx_hz) {
      lfxScaled = prefScaled.scaled_lfx_hz
    }
    smoothnessScaled = prefScaled.scaled_sm_pred_in_room

    const estimates = measurement.estimates
    if (estimates && estimates.ref_band) {
      flatness = estimates.ref_band
    }
    flatnessScaled = prefScaled.scaled_flatness
  }
  return {
    score: parseFloat(score).toFixed(1),
    lfx: lfx.toFixed(0),
    flatness: flatness.toFixed(1),
    smoothness: smoothness.toFixed(1),
    scoreScaled: scoreScaled.toFixed(1),
    lfxScaled: lfxScaled,
    flatnessScaled: flatnessScaled,
    smoothnessScaled: smoothnessScaled
  }
}

export function getLoading (key) {
  if (key < 12) {
    return 'eager'
  }
  return 'lazy'
}

export function getDecoding (key) {
  if (key < 12) {
    return 'sync'
  }
  return 'async'
}
