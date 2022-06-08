// import { Plotly } from '../../../node_modules/plotly/index.js'
import { urlSite } from './misc.js'
import { downloadZip } from './downloadzip.js'

const knownMeasurements = [
  'CEA2034',
  'CEA2034 with splitted views',
  'On Axis',
  'Estimated In-Room Response',
  'Early Reflections',
  'Horizontal Reflections',
  'Vertical Reflections',
  'SPL Horizontal',
  'SPL Horizontal Normalized',
  'SPL Vertical',
  'SPL Vertical Normalized',
  'SPL Horizontal Contour',
  'SPL Horizontal Contour Normalized',
  'SPL Vertical Contour',
  'SPL Vertical Contour Normalized',
  'SPL Horizontal 3D',
  'SPL Horizontal 3D Normalized',
  'SPL Vertical 3D',
  'SPL Vertical 3D Normalized',
  'SPL Horizontal Globe',
  'SPL Horizontal Globe Normalized',
  'SPL Vertical Globe',
  'SPL Vertical Globe Normalized',
  'SPL Horizontal Radar',
  'SPL Vertical Radar'
]

const colors = [
  '#5c77a5',
  '#dc842a',
  '#c85857',
  '#89b5b1',
  '#71a152',
  '#bab0ac',
  '#e15759',
  '#b07aa1',
  '#76b7b2',
  '#ff9da7'
]

const uniformColors = {
  // regression
  'Linear Regression': colors[0],
  'Band ±1.5dB': colors[1],
  'Band ±3dB': colors[1],
  // PIR
  'Estimated In-Room Response': colors[0],
  // spin
  'On Axis': colors[0],
  'Listening Window': colors[1],
  'Early Reflections': colors[2],
  'Sound Power': colors[3],
  'Early Reflections DI': colors[4],
  'Sound Power DI': colors[5],
  // reflections
  'Ceiling Bounce': colors[1],
  'Floor Bounce': colors[2],
  'Front Wall Bounce': colors[3],
  'Rear Wall Bounce': colors[4],
  'Side Wall Bounce': colors[5],
  //
  'Ceiling Reflection': colors[1],
  'Floor Reflection': colors[2],
  //
  Front: colors[1],
  Rear: colors[2],
  Side: colors[3],
  //
  'Total Early Reflection': colors[7],
  'Total Horizontal Reflection': colors[8],
  'Total Vertical Reflection': colors[9],
  // SPL
  '10°': colors[1],
  '20°': colors[2],
  '30°': colors[3],
  '40°': colors[4],
  '50°': colors[5],
  '60°': colors[6],
  '70°': colors[7],
  // Radars
  '500 Hz': colors[1],
  '1000 Hz': colors[2],
  '2000 Hz': colors[3],
  '10000 Hz': colors[4],
  '15000 Hz': colors[5]
}

const labelShort = {
  // regression
  'Linear Regression': 'Reg',
  'Band ±1.5dB': '±1.5dB',
  'Band ±3dB': '±3dB',
  // PIR
  'Estimated In-Room Response': 'PIR',
  // spin
  'On Axis': 'ON',
  'Listening Window': 'LW',
  'Early Reflections': 'ER',
  'Sound Power': 'SP',
  'Early Reflections DI': 'ERDI',
  'Sound Power DI': 'SPDI',
  // reflections
  'Ceiling Bounce': 'CB',
  'Floor Bounce': 'FB',
  'Front Wall Bounce': 'FWB',
  'Rear Wall Bounce': 'RWB',
  'Side Wall Bounce': 'SWB',
  //
  'Ceiling Reflection': 'CR',
  'Floor Reflection': 'FR',
  //
  Front: 'F',
  Rear: 'R',
  Side: 'S',
  //
  'Total Early Reflection': 'TER',
  'Total Horizontal Reflection': 'THR',
  'Total Vertical Reflection': 'TVR'
}

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.json()
  }).then((dataJson) => {
  const metadata = Object.values(dataJson)

  const urlCompare = urlSite + 'compare.html?'
  const metaSpeakers = {}
  const nbSpeakers = 2

  const queryString = window.location.search
  const urlParams = new URLSearchParams(queryString)

  const plotContainer = document.querySelector('[data-num="0"')
  const plotSingleContainer = plotContainer.querySelector('.plotSingle')
  const plotDouble0Container = plotContainer.querySelector('.plotDouble0')
  const plotDouble1Container = plotContainer.querySelector('.plotDouble1')
  const formContainer = plotContainer.querySelector('.plotForm')
  const graphsSelector = formContainer.querySelector('.graph')

  const windowWidth = window.innerWidth
  const windowHeight = window.innerHeight

  function getAllSpeakers () {
    const speakers = []
    metadata.forEach(function (value) {
      const speaker = value.brand + ' ' + value.model
      speakers.push(speaker)
      metaSpeakers[speaker] = value
    })
    return speakers.sort()
  }

  function processOrigin (origin) {
    if (origin.includes('Vendors-')) {
      return origin.slice(8)
    }
    return origin
  }

  function processGraph (name) {
    if (name.includes('CEA2034')) {
      return 'CEA2034'
    } else if (name.includes('3D')) {
      return name.replace('3D', 'Contour')
    } else if (name.includes('Globe')) {
      return name.replace('Globe', 'Contour')
    }
    return name
  }

  function getOrigin (speaker, origin) {
    // console.log('getOrigin ' + speaker + ' origin=' + origin)
    if (origin == null || origin === '') {
      const defaultMeasurement = metaSpeakers[speaker].default_measurement
      const defaultOrigin = metaSpeakers[speaker].measurements[defaultMeasurement].origin
      // console.log('getOrigin default=' + defaultOrigin)
      return processOrigin(defaultOrigin)
    }
    return processOrigin(origin)
  }

  function getVersion (speaker, origin, version) {
    if (version == null || version === '') {
      const defaultVersion = metaSpeakers[speaker].default_measurement
      return defaultVersion
    }
    return version
  }

  function getSpeakerData (graph, speaker, origin, version) {
    // console.log('getSpeakerData ' + graph + ' speaker=' + speaker + ' origin=' + origin + ' version=' + version)
    const url =
          urlSite +
          'speakers/' +
            speaker + '/' +
            getOrigin(speaker, origin) + '/' +
            getVersion(speaker, origin, version) + '/' +
            processGraph(graph) + '.json.zip'
    // console.log('fetching url=' + url)
    const spec = downloadZip(url).then(function (spec) {
      // console.log('parsing url=' + url)
      const js = JSON.parse(spec)
      return js
    }).catch((error) => {
      console.log('ERROR getSpeaker data 404 ' + error)
      return null
    })
    return spec
  }

  function setLayoutAndDataPrimary (spin) {
    let layout = null
    let datas = null
    // console.log('layout and data: ' + spin.length)
    if (spin[0] != null && spin[1] != null) {
      layout = spin[0].layout
      datas = spin[0].data.concat(spin[1].data)
    } else if (spin[0] != null) {
      layout = spin[0].layout
      datas = spin[0].data
    } else if (spin[1] != null) {
      layout = spin[1].layout
      datas = spin[1].data
    }
    if (layout != null && datas != null) {
      if (windowWidth < 400 || windowHeight < 400) {
        layout.width = windowWidth
        layout.height = Math.max(360, Math.min(windowHeight, windowWidth * 0.7 + 100))
        layout.margin = {
          l: 0,
          r: 0,
          t: 40,
          b: 20
        }
        layout.legend = {
          orientation: 'h',
          y: -0.5,
          x: 0,
          xanchor: 'bottom',
          yanchor: 'left'
        }
        for (let k = 0; k < datas.length; k++) {
          if (datas[k].name && labelShort[datas[k].name]) {
            datas[k].name = labelShort[datas[k].name]
          }
        }
      } else {
        layout.width = windowWidth - 40
        layout.height = Math.max(800, Math.min(windowHeight - 40, windowWidth * 0.7 + 140))
        layout.margin = {
          l: 15,
          r: 15,
          t: 30,
          b: 50
        }
        layout.legend = {
          orientation: 'h',
          y: -0.1,
          x: 0,
          xanchor: 'bottom',
          yanchor: 'left'
        }
      }
      layout.title = null
      layout.font = { size: 16 }
      if (layout.xaxis) {
        layout.xaxis.autotick = false
      }
      if (layout.yaxis) {
        layout.yaxis.dtick = 1
      }
      plotSingleContainer.style.display = 'block'
      plotDouble0Container.style.display = 'none'
      plotDouble1Container.style.display = 'none'
      Plotly.newPlot('plotSingle', datas, layout, { responsive: true })
    } else {
      // should be a pop up
      console.log('Error: No graph available')
    }
  }

  function setCEA2034 (speakerNames, speakerGraphs) {
    // console.log('setCEA2034 got ' + speakerGraphs.length + ' graphs')
    for (let i = 0; i < speakerGraphs.length; i++) {
      if (speakerGraphs[i] != null) {
        // console.log('adding graph ' + i)
        for (const trace in speakerGraphs[i].data) {
          speakerGraphs[i].data[trace].legendgroup = 'speaker' + i
          speakerGraphs[i].data[trace].legendgrouptitle = { text: speakerNames[i] }
          if (i % 2 === 1) {
            speakerGraphs[i].data[trace].line = { dash: 'dashdot' }
          }
        }
      }
    }
    setLayoutAndDataPrimary(speakerGraphs)
  }

  function setCEA2034Split (speakerNames, speakerGraphs) {
    // console.log('setCEA2034Split got ' + speakerGraphs.length + ' graphs')
    for (let i = 0; i < speakerGraphs.length; i++) {
      if (speakerGraphs[i] != null) {
        // console.log('adding graph ' + i)
        for (const trace in speakerGraphs[i].data) {
          speakerGraphs[i].data[trace].legendgroup = 'speaker' + i
          speakerGraphs[i].data[trace].legendgrouptitle = { text: speakerNames[i] }
          if (i % 2 === 1) {
            speakerGraphs[i].data[trace].line = { dash: 'dashdot' }
          }
        }
      }
    }
    let layout = null
    let datas = null

    if (speakerGraphs[0] != null && speakerGraphs[1] != null) {
      layout = speakerGraphs[0].layout
      datas = speakerGraphs[0].data.concat(speakerGraphs[1].data)

      layout.width = windowWidth - 40
      layout.height = Math.max(360, Math.min(windowHeight, windowWidth * 0.7 + 140))
      layout.title = null
      layout.font = { size: 16 }
      layout.margin = {
        l: 15,
        r: 15,
        t: 30,
        b: 30
      }
      layout.legend = {
        orientation: 'h',
        y: -0.1,
        x: 0,
        xanchor: 'bottom',
        yanchor: 'left',
        itemclick: 'toggleothers'
      }

      plotSingleContainer.style.display = 'block'
      Plotly.newPlot('plotSingle', datas, layout, { responsive: true })

      const deltas = []
      for (const g0 in speakerGraphs[0].data) {
        const name0 = speakerGraphs[0].data[g0].name
        const deltasX = speakerGraphs[0].data[g0].x
        for (const g1 in speakerGraphs[1].data) {
          if (name0 === speakerGraphs[1].data[g1].name) {
            const deltasY = []
            for (const i in speakerGraphs[0].data[g0].y) {
              deltasY[i] = speakerGraphs[0].data[g0].y[i] - speakerGraphs[1].data[g1].y[i]
            }
            deltas.push({
              x: deltasX,
              y: deltasY,
              type: 'scatter',
              name: name0,
              // "legendgroup": "differences",
              // "legendgrouptitle": {
              //    "text": 'Differences',
              // },
              marker: {
                color: uniformColors[name0]
              }
            })
          }
        }
      }
      // console.log(deltas.length)
      // deltas.forEach( (data) => console.log(data.name) );

      const layout2 = JSON.parse(JSON.stringify(layout))
      layout2.height = 440
      layout2.yaxis = {
        title: 'Delta SPL (dB)',
        range: [-5, 5],
        dtick: 1
      }
      layout2.showlegend = true
      layout2.legend = layout.legend
      layout2.legend.y = -0.3
      layout2.margin = layout.margin
      plotDouble0Container.style.display = 'block'
      Plotly.newPlot('plotDouble0', deltas, layout2, { responsive: true })
      plotDouble1Container.style.display = 'none'
    } else {
      setLayoutAndDataPrimary(speakerGraphs)
    }
  }

  function setGraph (speakerNames, speakerGraphs) {
    // console.log('setGraph got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    for (const i in speakerGraphs) {
      if (speakerGraphs[i] != null) {
        // console.log('adding graph ' + i)
        for (const trace in speakerGraphs[i].data) {
          speakerGraphs[i].data[trace].legendgroup = 'speaker' + i
          speakerGraphs[i].data[trace].legendgrouptitle = { text: speakerNames[i] }
          if (i % 2 === 1) {
            speakerGraphs[i].data[trace].line = { dash: 'dashdot' }
          }
        }
      }
    }
    setLayoutAndDataPrimary(speakerGraphs)
  }

  function setContour (speakerNames, speakerGraphs) {
    // console.log('setContour got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    plotSingleContainer.style.display = 'none'
    plotDouble0Container.style.display = 'block'
    plotDouble1Container.style.display = 'block'
    for (const i in speakerGraphs) {
      if (speakerGraphs[i]) {
        for (const j in speakerGraphs[i].data) {
          speakerGraphs[i].data[j].legendgroup = 'speaker' + i
          speakerGraphs[i].data[j].legendgrouptitle = { text: speakerNames[i] }
        }
        const datas = speakerGraphs[i].data
        const layout = speakerGraphs[i].layout

        Plotly.newPlot('plotDouble' + i, datas, layout, { responsive: true })
      }
    }
  }

  const contourMin = -30
  const contourMax = 3
  const contourColorscale = [
    [0, 'rgb(0,0,168)'],
    [0.1, 'rgb(0,0,200)'],
    [0.2, 'rgb(0,74,255)'],
    [0.3, 'rgb(0,152,255)'],
    [0.4, 'rgb(74,255,161)'],
    [0.5, 'rgb(161,255,74)'],
    [0.6, 'rgb(255,255,0)'],
    [0.7, 'rgb(234,159,0)'],
    [0.8, 'rgb(255,74,0)'],
    [0.9, 'rgb(222,74,0)'],
    [1, 'rgb(253,14,13)']
  ]

  function setGlobe (speakerNames, speakerGraphs) {
    // console.log('setGlobe ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    plotSingleContainer.style.display = 'none'
    plotDouble0Container.style.display = 'block'
    plotDouble1Container.style.display = 'block'
    for (const i in speakerGraphs) {
      if (speakerGraphs[i]) {
        let polarData = []
        for (const j in speakerGraphs[i].data) {
          const x = speakerGraphs[i].data[j].x
          const y = speakerGraphs[i].data[j].y
          const z = speakerGraphs[i].data[j].z
          if (!z) {
            continue
          }
          const r = []
          // r is x (len of y times)
          for (let k1 = 0; k1 < x.length; k1++) {
            for (let k2 = 0; k2 < y.length - 1; k2++) {
              r.push(Math.log10(x[k1]))
            }
          }
          // theta is y (len of x times)
          let theta = []
          for (let k = 0; k < x.length; k++) {
            for (let k2 = 0; k2 < y.length - 1; k2++) {
              theta.push(y[k2])
            }
          }
          theta = theta.flat()
          // color is z unravelled
          // console.log('debug: len(speakerGraphs[' + i + '].data[' + j + '].x=' + x.length)
          // console.log('debug: len(speakerGraphs[' + i + '].data[' + j + '].y=' + y.length)
          // console.log('debug: len(speakerGraphs[' + i + '].data[' + j + '].z=' + z.length)
          const color = []
          for (let k1 = 0; k1 < x.length; k1++) {
            for (let k2 = 0; k2 < y.length - 1; k2++) {
              let val = z[k2][k1]
              val = Math.max(contourMin, val)
              val = Math.min(contourMax, val)
              color.push(val)
            }
          }
          let currentPolarData = {}
          currentPolarData.type = 'barpolar'
          currentPolarData.r = r
          currentPolarData.theta = theta
          currentPolarData.marker = {
            autocolorscale: false,
            colorscale: contourColorscale,
            color: color,
            colorbar: {
              title: {
                text: 'dB (SPL)'
              }
            },
            showscale: true,
            line: {
              color: null,
              width: 0
            }
          }
          currentPolarData.legendgroup = 'speaker' + i
          currentPolarData.legendgrouptitle = { text: speakerNames[i] }

          polarData.push(currentPolarData)
        }
        const layout = speakerGraphs[i].layout
        layout.polar = {
          bargap: 0,
          hole: 0.05
        }
        Plotly.newPlot('plotDouble' + i, polarData, layout, { responsive: true })
      }
    }
  }

  function setSurface (speakerNames, speakerGraphs) {
    // console.log('setSurface ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    plotSingleContainer.style.display = 'none'
    plotDouble0Container.style.display = 'block'
    plotDouble1Container.style.display = 'block'
    for (const i in speakerGraphs) {
      if (speakerGraphs[i]) {
        let surfaceData = []
        for (const j in speakerGraphs[i].data) {
          // console.log('debug: speakerGraphs[' + i + '].data[' + j + '].x ' + speakerGraphs[i].data[j].x.length)
          // console.log('debug: speakerGraphs[' + i + '].data[' + j + '].y ' + speakerGraphs[i].data[j].y.length)
          // TODO: debug that we get the right angles
          speakerGraphs[i].data[j].y = speakerGraphs[i].data[j].y.slice(10, -10)
          if (!speakerGraphs[i].data[j].z) {
            continue
          }
          // console.log('debug: speakerGraphs[' + i + '].data[' + j + '].z ' + speakerGraphs[i].data[j].z.length)
          // TODO: debug that we get the right angles
          let currentSurfaceData = {}
          currentSurfaceData.x = speakerGraphs[i].data[j].x
          currentSurfaceData.y = speakerGraphs[i].data[j].y
          currentSurfaceData.z = speakerGraphs[i].data[j].z.slice(10, -10)
          currentSurfaceData.type = 'surface'
          currentSurfaceData.legendgroup = 'speaker' + i
          currentSurfaceData.legendgrouptitle = { text: speakerNames[i] }

          surfaceData.push(currentSurfaceData)
        }
        const layout = speakerGraphs[i].layout
        layout.autosize = false
        layout.width = windowWidth
        layout.height = (windowHeight - 100) / 2
        layout.yaxis = {
          range: [-60, 60]
        }
        layout.zaxis = {
          range: [-20, 5]
        }
        Plotly.newPlot('plotDouble' + i, surfaceData, layout, { responsive: true })
      }
    }
  }

  function plot (measurement, speakersName, speakersGraph) {
    // console.log('plot: ' + speakersName.length + ' names and ' + speakersGraph.length + ' graphs')
    async function run () {
      Promise.all(speakersGraph).then((graphs) => {
        // console.log('plot: resolved ' + graphs.length + ' graphs')
        if (measurement === 'CEA2034') {
          return setCEA2034(speakersName, graphs)
        } else if (measurement === 'CEA2034 with splitted views') {
          return setCEA2034Split(speakersName, graphs)
        } else if (measurement === 'On Axis' ||
                    measurement === 'Estimated In-Room Response' ||
                    measurement === 'Early Reflections' ||
                    measurement === 'SPL Horizontal' ||
                    measurement === 'SPL Vertical' ||
                    measurement === 'SPL Horizontal Normalized' ||
                    measurement === 'SPL Vertical Normalized' ||
                    measurement === 'Horizontal Reflections' ||
                    measurement === 'Vertical Reflections' ||
                    measurement === 'SPL Horizontal Radar' ||
                    measurement === 'SPL Vertical Radar') {
          return setGraph(speakersName, graphs)
        } else if (measurement === 'SPL Horizontal Contour' ||
                    measurement === 'SPL Vertical Contour' ||
                    measurement === 'SPL Horizontal Contour Normalized' ||
                    measurement === 'SPL Vertical Contour Normalized') {
          return setContour(speakersName, graphs)
        } else if (measurement === 'SPL Horizontal 3D' ||
                    measurement === 'SPL Vertical 3D' ||
                    measurement === 'SPL Horizontal 3D Normalized' ||
                    measurement === 'SPL Vertical 3D Normalized') {
          return setSurface(speakersName, graphs)
        } else if (measurement === 'SPL Horizontal Globe' ||
                    measurement === 'SPL Vertical Globe' ||
                    measurement === 'SPL Horizontal Globe Normalized' ||
                    measurement === 'SPL Vertical Globe Normalized') {
          return setGlobe(speakersName, graphs)
        } // todo add multi view
        return null
      })
    }
    run()
  }

  function assignOptions (textArray, selector, textSelected) {
    // console.log('assignOptions: selected = ' + textSelected)
    // textArray.forEach( item => // console.log('assignOptions: '+item));
    while (selector.firstChild) {
      selector.firstChild.remove()
    }
    for (let i = 0; i < textArray.length; i++) {
      const currentOption = document.createElement('option')
      currentOption.text = textArray[i]
      if (textArray[i] === textSelected) { currentOption.selected = true }
      if (textArray.length === 1) { currentOption.disabled = true }
      selector.appendChild(currentOption)
    }
  }

  function buildInitSpeakers (speakers, count) {
    const list = []
    for (let pos = 0; pos < count; pos++) {
      if (urlParams.has('speaker' + pos)) {
        list[pos] = urlParams.get('speaker' + pos)
        continue
      }
      list[pos] = speakers[Math.floor(Math.random() * speakers.length)]
    }
    return list
  }

  function buildInitMeasurement () {
    if (urlParams.has('measurement')) {
      const m = urlParams.get('measurement')
      if (knownMeasurements.includes(m)) {
        return m
      }
    }
    return knownMeasurements[0]
  }

  const speakers = getAllSpeakers()
  const initSpeakers = buildInitSpeakers(speakers, nbSpeakers)
  const initMeasurement = buildInitMeasurement()
    
  const speakersSelector = []
  const originsSelector = []
  const versionsSelector = []
  for (let pos = 0; pos < nbSpeakers; pos++) {
    const tpos = pos.toString()
    speakersSelector[pos] = formContainer.querySelector('.speaker' + tpos)
    originsSelector[pos] = formContainer.querySelector('.origin' + tpos)
    versionsSelector[pos] = formContainer.querySelector('.version' + tpos)
  }

  for (let pos = 0; pos < nbSpeakers; pos++) {
    assignOptions(speakers, speakersSelector[pos], initSpeakers[pos])
  }
  assignOptions(knownMeasurements, graphsSelector, initMeasurement)

  function updateVersion (speaker, selector, origin, value) {
    // update possible version(s) for matching speaker and origin
    // console.log('update version for ' + speaker + ' origin=' + origin + ' value=' + value)
    const versions = Object.keys(metaSpeakers[speaker].measurements)
    let matches = []
    versions.forEach((val) => {
      const current = metaSpeakers[speaker].measurements[val]
      if (current.origin === origin || origin === '' || origin == null) {
        matches.push(val)
      }
    })
    if (metaSpeakers[speaker].eq != null) {
      const matchesEQ = []
      for (const key in matches) {
        matchesEQ.push(matches[key] + '_eq')
      }
      matches = matches.concat(matchesEQ)
    }
    if (value != null) {
      assignOptions(matches, selector, value)
    } else {
      assignOptions(matches, selector, selector.value)
    }
  }

  function updateOrigin (speaker, originSelector, versionSelector, origin, version) {
    // console.log('updateOrigin for ' + speaker + ' with origin ' + origin + ' version=' + version)
    const measurements = Object.keys(metaSpeakers[speaker].measurements)
    const origins = new Set()
    for (const key in measurements) {
      origins.add(metaSpeakers[speaker].measurements[measurements[key]].origin)
    }
    const [first] = origins
    // console.log('updateOrigin found this possible origins: ' + origins.size + ' first=' + first)
    // origins.forEach(item => console.log('updateOrigin: ' + item))
    if (origin != null) {
      assignOptions(Array.from(origins), originSelector, origin)
    } else {
      assignOptions(Array.from(origins), originSelector, first)
    }
    updateVersion(speaker, versionSelector, originSelector.value, version)
  }

  function updateSpeakers () {
    const names = []
    const graphs = []
    for (let i = 0; i < nbSpeakers; i++) {
      graphs[i] = getSpeakerData(
        graphsSelector.value,
        speakersSelector[i].value,
        originsSelector[i].value,
        versionsSelector[i].value
      )
      names[i] = speakersSelector[i].value
    }
    urlParams.set('measurement', graphsSelector.value)
    history.pushState({ page: 1 },
      'Change measurement',
      urlCompare + urlParams.toString()
    )
    plot(graphsSelector.value, names, graphs)
  }

  function updateSpeakerPos (pos) {
    // console.log('updateSpeakerPos(' + pos + ')')
    updateOrigin(speakersSelector[pos].value, originsSelector[pos], versionsSelector[pos])
    urlParams.set('speaker' + pos, speakersSelector[pos].value)
    history.pushState({ page: 1 },
      'Compare speakers',
      urlCompare + urlParams.toString()
    )
    updateSpeakers()
  }

  function updateVersionPos (pos) {
    // console.log('updateVersionsPos(' + pos + ')')
    updateVersion(
      speakersSelector[pos].value,
      versionsSelector[pos],
      originsSelector[pos].value,
      versionsSelector[pos].value
    )
    updateSpeakers()
    urlParams.set('version' + pos, versionsSelector[pos].value)
    history.pushState({ page: 1 },
      'Compare speakers',
      urlCompare + urlParams.toString()
    )
  }

  function updateOriginPos (pos) {
    // console.log('updateOriginPos(' + pos + ')')
    updateOrigin(speakersSelector[pos].value, originsSelector[pos], versionsSelector[pos], originsSelector[pos].value)
    urlParams.set('origin' + pos, originsSelector[pos].value)
    history.pushState({ page: 1 },
      'Compare speakers',
      urlCompare + urlParams.toString()
    )
    updateSpeakers()
  }

  // initial setup
  const initDatas = []
  for (let pos = 0; pos < nbSpeakers; pos++) {
    updateOrigin(
      initSpeakers[pos],
      originsSelector[pos],
      versionsSelector[pos],
      urlParams.get('origin' + pos),
      urlParams.get('version' + pos)
    )
    updateOriginPos(pos)
    updateSpeakerPos(pos)
    // console.log('DEBUG: ' + originsSelector[pos].options[0])
    initDatas[pos] = getSpeakerData(initMeasurement, initSpeakers[pos], null, null)
  }

  // add listeners
  graphsSelector.addEventListener('change', updateSpeakers, false)

  for (let pos = 0; pos < nbSpeakers; pos++) {
    speakersSelector[pos].addEventListener('change', () => { return updateSpeakerPos(pos) }, false)
    originsSelector[pos].addEventListener('change', () => { return updateOriginPos(pos) }, false)
    versionsSelector[pos].addEventListener('change', () => { return updateVersionPos(pos) }, false)
  }

  plot(initMeasurement, initSpeakers, initDatas)
}).catch(err => console.log(err.message))
