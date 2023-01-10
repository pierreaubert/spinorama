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

  const urlCompare = urlSite + 'compare.html?'
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

  function plot (measurement, speakersName, speakersGraph) {
    // console.log('plot: ' + speakersName.length + ' names and ' + speakersGraph.length + ' graphs')
    async function run () {
      Promise.all(speakersGraph).then((graphs) => {
        // console.log('plot: resolved ' + graphs.length + ' graphs')
        let graphsConfigs = []
        if (measurement === 'CEA2034') {
          graphsConfigs = setCEA2034(speakersName, graphs, windowWidth, windowHeight)
        } else if (measurement === 'CEA2034 with splitted views') {
          graphsConfigs = setCEA2034Split(speakersName, graphs, windowWidth, windowHeight)
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
          graphsConfigs = setGraph(speakersName, graphs, windowWidth, windowHeight)
        } else if (measurement === 'SPL Horizontal Contour' ||
                   measurement === 'SPL Vertical Contour' ||
                   measurement === 'SPL Horizontal Contour Normalized' ||
                   measurement === 'SPL Vertical Contour Normalized') {
          graphsConfigs = setContour(speakersName, graphs, windowWidth, windowHeight)
        } else if (measurement === 'SPL Horizontal 3D' ||
                    measurement === 'SPL Vertical 3D' ||
                    measurement === 'SPL Horizontal 3D Normalized' ||
                    measurement === 'SPL Vertical 3D Normalized') {
          graphsConfigs = setSurface(speakersName, graphs, windowWidth, windowHeight)
        } else if (measurement === 'SPL Horizontal Globe' ||
                    measurement === 'SPL Vertical Globe' ||
                    measurement === 'SPL Horizontal Globe Normalized' ||
                    measurement === 'SPL Vertical Globe Normalized') {
          graphsConfigs = setGlobe(speakersName, graphs, windowWidth, windowHeight)
        } // todo add multi view

        // console.log('datas and layouts length='+graphsConfigs.length)
        if ( graphsConfigs.length === 1 ) {
          plotSingleContainer.style.display = 'block'
          plotDouble0Container.style.display = 'none'
          plotDouble1Container.style.display = 'none'
          const config = graphsConfigs[0]
          if (config) {
            Plotly.newPlot('plotSingle', config)
          }
        } else if (graphsConfigs.length === 2 ) {
          plotSingleContainer.style.display = 'none'
          plotDouble0Container.style.display = 'block'
          plotDouble1Container.style.display = 'block'
          for( let i = 0 ; i<graphsConfigs.length ; i++) {
            let config = graphsConfigs[i]
            if (config) {
              Plotly.newPlot('plotDouble' + i, config)
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
    return knownMeasurements[0]
  }

  function updateSpeakers () {
    const names = []
    const graphs = []
    for (let i = 0; i < nbSpeakers; i++) {
      graphs[i] = getSpeakerData(
        metaSpeakers,
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
    updateOrigin(metaSpeakers, speakersSelector[pos].value, originsSelector[pos], versionsSelector[pos])
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
      metaSpeakers,
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
    updateOrigin(metaSpeakers, speakersSelector[pos].value, originsSelector[pos], versionsSelector[pos], originsSelector[pos].value)
    urlParams.set('origin' + pos, originsSelector[pos].value)
    history.pushState({ page: 1 },
                      'Compare speakers',
                      urlCompare + urlParams.toString()
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
  for (let pos = 0; pos < nbSpeakers; pos++) {
    updateOrigin(
      metaSpeakers,
      initSpeakers[pos],
      originsSelector[pos],
      versionsSelector[pos],
      urlParams.get('origin' + pos),
      urlParams.get('version' + pos)
    )
    updateOriginPos(pos)
    updateSpeakerPos(pos)
    // console.log('DEBUG: ' + originsSelector[pos].options[0])
    initDatas[pos] = getSpeakerData(metaSpeakers, initMeasurement, initSpeakers[pos], null, null)
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
