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
    let originLong = measurement.origin
    const url = 'speakers/' + value.brand + ' ' + value.model + '/' + removeVendors(origin) + '/index_' + version + '.html'
    if (origin === 'Misc') {
      origin = version.replace('misc-', '')
      originLong = version.replace('misc-', '')
    } else {
      origin = origin.replace('Vendors-', '')
      originLong = origin.replace('Vendors-', '')
      if (origin === 'Kling Freitag') {
        origin = 'K&F'
      }
      else if (origin === 'Alcons Audio') {
        origin = 'AA'
      }
    }
    if (origin === 'ErinsAudioCorner') {
      origin = 'EAC'
    } else if (origin === 'Princeton') {
      origin = 'PCT'
    } else if (origin === 'napilopez') {
      origin = 'NPZ'
    } else if (origin === 'speakerdata2034') {
      origin = 'SPK'
    } else if (origin === 'archimago') {
      origin = 'AMG'
    } else if (origin === 'audioxpress') {
      origin = 'AXP'
    } else if (origin === 'audioholics') {
      origin = 'AHL'
    } else if (origin === 'soundstageultra') {
      origin = 'SSU'
    } else if (origin === 'sr') {
      origin = 'S&R'
    } else if (origin.search('nuyes') != -1 ) {
      origin = "NYS"
    }

    origin = origin.charAt(0).toUpperCase() + origin.slice(1)
    originLong = originLong.charAt(0).toUpperCase() + origin.slice(1)
    if (version.search("sealed") != -1 ) {
      origin = origin + " (Sealed)"
      originLong = originLong + " (Sealed)"
    } else if  (version.search("vented") != -1 ) {
      origin = origin + " (Vented)"
      originLong = originLong + " (Vented)"
    } else if  (version.search("ported") != -1 ) {
      origin = origin + " (Ported)"
      originLong = originLong + " (Ported)"
    }

    if (version.search("grille-on") != -1 ) {
      origin = origin + " (Grille on)"
      originLong = originLong + " (Grille on)"
    } else if  (version.search("no-grille") != -1 ) {
      origin = origin + " (Grille off)"
      originLong = originLong + " (Grille off)"
    }

    if (version.search("short-port") != -1 ) {
      origin = origin + " (Short Port)"
      originLong = originLong + " (Short Port)"
    } else if  (version.search("long-port") != -1 ) {
      origin = origin + " (Long Port)"
      originLong = originLong + " (Long Port)"
    }

    if (version.search("bassreflex") != -1 ) {
      origin = origin + " (BR)"
      originLong = originLong + " (Bass Reflex)"
    } else if  (version.search("cardioid") != -1 ) {
      origin = origin + " (C)"
      originLong = originLong + " (Cardiod)"
    }     

    if (version.search("fullrange") != -1 ) {
      origin = origin + " (FR)"
      originLong = originLong + " (Full Range)"
    } else if  (version.search("lowcut") != -1 ) {
      origin = origin + " (LC)"
      originLong = originLong + " (Low Cut)"
    }     

    if (version.search("active") != -1 ) {
      origin = origin + " (Act.)"
      originLong = originLong + " (Active)"
    } else if  (version.search("passive") != -1 ) {
      origin = origin + " (Pas.)"
      originLong = originLong + " (Passive)"
    }     

    if (version.search("horizontal") != -1 ) {
      origin = origin + " (Hor.)"
      originLong = originLong + " (Horizontal)"
    } else if  (version.search("vertical") != -1 ) {
      origin = origin + " (Ver.)"
      originLong = originLong + " (Vertical)"
    }

    if (version.search("gll") != -1 ) {
      origin = origin + " (gll)"
      originLong = originLong + " (gll)"
    } else if  (version.search("klippel") != -1 ) {
      origin = origin + " (klippel)"
      originLong = originLong + " (klippel)"
    }

    if (version.search("wide") != -1 ) {
      origin = origin.slice(0, origin.length-1) + "/W)"
      originLong = originLong.slice(0, originLong.length-1) + "/Wide)"
    } else if  (version.search("narrow") != -1 ) {
      origin = origin.slice(0, origin.length-1) + "/N)"
      originLong = originLong.slice(0, originLong.length-1) + "/Narrow)"
    } else if  (version.search("medium") != -1 ) {
      origin = origin.slice(0, origin.length-1) + "/M)"
      originLong = originLong.slice(0, originLong.length-1) + "/Medium)"
    }

    const ipattern = version.search("pattern")
    if (ipattern != -1 ) {
      const sversion = version.slice(ipattern+8)
      if (sversion.search(/[0-9]*/) != -1) {
        const sversionTimes = sversion.indexOf('x')
        let sversionDeg = sversion
        if (sversionTimes != -1) {
          sversionDeg = ' ' + sversion.slice(0, sversionTimes) + "º" + sversion.slice(sversionTimes) + "º"
        } else {
          sversionDeg = ' ' + sversion + "º"
        }
        origin = origin + sversionDeg
        originLong = originLong + sversionDeg
      }
    } 

    // version
    const posVersion = version.search(/-v[123456]-/)
    if (posVersion != -1 ) {
      origin = origin + " (v" + version[posVersion+2] + ")"
      originLong = originLong + " (v" + version[posVersion+2] + ")"
    }

    // counter
    const posCounter = version.search(/-v[123456]x/)
    if (posCounter != -1 ) {
      origin = origin + " (" + version[posCounter+2] + "x)"
      originLong = originLong + " (" + version[posCounter+2] + "x)"
    }

    reviews.push({
      url: encodeURI(url),
      origin: origin,
      originLong: originLong,
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

