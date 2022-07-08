import { urlSite } from './misc.js'
import {
  assignOptions,
  knownMeasurements,
  getAllSpeakers,
  getSpeakerData,
  setContour,
  setGlobe,
  setGraph,
  setCEA2034,
  setCEA2034Split,
  setSurface,
  updateOrigin,
  updateVersion,
} from './common.js'

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.json()
}).then((dataJson) => {
  const metadata = Object.values(dataJson)

  const urlSimilar = urlSite + 'similar.html?'
  const nbSpeakers = 1

  const queryString = window.location.search
  const urlParams = new URLSearchParams(queryString)

  const plotContainer = document.querySelector('[data-num="0"')
  const plotDouble0Container = plotContainer.querySelector('.plotDouble0')
  const plotDouble1Container = plotContainer.querySelector('.plotDouble1')
  const plotDouble2Container = plotContainer.querySelector('.plotDouble2')
  const formContainer = plotContainer.querySelector('.plotForm')
  const graphsSelector = formContainer.querySelector('.graph')

  const windowWidth = window.innerWidth
  const windowHeight = window.innerHeight

  function plot (measurement, speakersName, speakersGraph) {
    console.log('plot: ' + speakersName.length + ' names and ' + speakersGraph.length + ' graphs')
    async function run () {
      Promise.all(speakersGraph).then((graphs) => {
        console.log('plot: resolved ' + graphs.length + ' graphs')
        for( let i=0 ; i<graphs.length-1; i++ ) {
          let datasAndLayouts = []
          let currentGraphs = [graphs[0], graphs[i+1]]
          let currentNames = [speakersName[0], speakersName[i+1]]
          if (measurement === 'CEA2034') {
            datasAndLayouts = setCEA2034(currentNames, currentGraphs, windowWidth, windowHeight)
          } else if (measurement === 'CEA2034 with splitted views') {
            datasAndLayouts = setCEA2034Split(currentNames, currentGraphs, windowWidth, windowHeight)
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
            datasAndLayouts = setGraph(currentNames, currentGraphs, windowWidth, windowHeight)
          } else if (measurement === 'SPL Horizontal Contour' ||
                     measurement === 'SPL Vertical Contour' ||
                     measurement === 'SPL Horizontal Contour Normalized' ||
                     measurement === 'SPL Vertical Contour Normalized') {
            datasAndLayouts = setContour(currentNames, currentGraphs, windowWidth, windowHeight)
          } else if (measurement === 'SPL Horizontal 3D' ||
                     measurement === 'SPL Vertical 3D' ||
                     measurement === 'SPL Horizontal 3D Normalized' ||
                     measurement === 'SPL Vertical 3D Normalized') {
            datasAndLayouts = setSurface(currentNames, currentGraphs, windowWidth, windowHeight)
          } else if (measurement === 'SPL Horizontal Globe' ||
                     measurement === 'SPL Vertical Globe' ||
                     measurement === 'SPL Horizontal Globe Normalized' ||
                     measurement === 'SPL Vertical Globe Normalized') {
            datasAndLayouts = setGlobe(currentNames, currentGraphs, windowWidth, windowHeight)
          } // todo add multi view
          console.log('datas and layouts length='+datasAndLayouts.length)
          if (datasAndLayouts.length === 1 ) {
            let [datas, layout] = datasAndLayouts[0]
            if (datas != null && layout != null ) {
              Plotly.newPlot('plotDouble' + i, datas, layout, { responsive: true })
            }
          }
        }
        return null
      })
    }
    run()
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
    return knownMeasurements[3] // PIR
  }

  function updateSpeakers () {
    const names = []
    const graphs = []
    graphs.push(
      getSpeakerData(
        metaSpeakers,
        graphsSelector.value,
        speakersSelector[0].value,
        originsSelector[0].value,
        versionsSelector[0].value
      ))
      names[0] = speakersSelector[0].value
    let similars = metaSpeakers[names[0]].nearest
    for( let i=0 ; i < similars.length ; i++ ) {
      console.log('adding '+similars[i][1])
      names.push(similars[i][1])
      graphs.push(
        getSpeakerData(
          metaSpeakers,
          graphsSelector.value,
          similars[i][1],
          null,
          null)
      )
    }
    urlParams.set('measurement', graphsSelector.value)
    history.pushState({ page: 1 },
                      'Change measurement',
                      urlSimilar + urlParams.toString()
                     )
    plot(graphsSelector.value, names, graphs)
  }
  
  function updateSpeakerPos (pos) {
    // console.log('updateSpeakerPos(' + pos + ')')
    updateOrigin(metaSpeakers, speakersSelector[pos].value, originsSelector[pos], versionsSelector[pos])
    urlParams.set('speaker' + pos, speakersSelector[pos].value)
    history.pushState({ page: 1 },
                      'Similar speakers',
                      urlSimilar + urlParams.toString()
                     )
    updateSpeakers()
  }
  
  function updateVersionPos (pos) {
    // console.log('updateVersionsPos(' + pos + ')')
    updateVersion(
      metaSpeakers,
      speakersSelector[pos].value,
      versionsSelector[pos],
      originsSelector[pos].value,
      versionsSelector[pos].value
    )
    updateSpeakers()
    urlParams.set('version' + pos, versionsSelector[pos].value)
    history.pushState({ page: 1 },
                      'Similar speakers',
                      urlSimilar + urlParams.toString()
                     )
  }
  
  function updateOriginPos (pos) {
    // console.log('updateOriginPos(' + pos + ')')
    updateOrigin(metaSpeakers, speakersSelector[pos].value, originsSelector[pos], versionsSelector[pos], originsSelector[pos].value)
    urlParams.set('origin' + pos, originsSelector[pos].value)
    history.pushState({ page: 1 },
                      'Similar speakers',
                      urlSimilar + urlParams.toString()
                     )
    updateSpeakers()
  }
  
  const [metaSpeakers, speakers] = getAllSpeakers(metadata);
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

  // initial setup
  const initDatas = []
  updateOrigin(
    metaSpeakers,
    initSpeakers[0],
    originsSelector[0],
    versionsSelector[0],
    urlParams.get('origin' + 0),
    urlParams.get('version' + 0)
  )
  updateOriginPos(0)
  updateSpeakerPos(0)
  // console.log('DEBUG: ' + originsSelector[pos].options[0])
  initDatas[0] = getSpeakerData(metaSpeakers, initMeasurement, initSpeakers[0], null, null)
  // lookup if we have similar speakers
  let similars = metaSpeakers[initSpeakers[0]].nearest
  console.log(similars)
  for( let i=0 ; i < similars.length ; i++ ) {
    console.log('adding '+similars[i][1])
    initSpeakers.push(similars[i][1])
    initDatas.push(getSpeakerData(metaSpeakers, initMeasurement, similars[i][1], null, null))
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
