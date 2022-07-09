import { urlSite } from './misc.js'
import {
  assignOptions,
  knownMeasurements,
  getSpeakerData,
  setContour,
  setGlobe,
  setGraph,
  setCEA2034,
  setCEA2034Split,
  setSurface,
} from './common.js'

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.json()
}).then((dataJson) => {
  const metadata = Object.values(dataJson)

  const urlSimilar = urlSite + 'similar.html?'

  const queryString = window.location.search
  const urlParams = new URLSearchParams(queryString)

  const plotContainer = document.querySelector('[data-num="0"')
  const formContainer = plotContainer.querySelector('.plotForm')
  const graphSelector = formContainer.querySelector('.graph')
  const speakerSelector = formContainer.querySelector('.speaker0')

  const windowWidth = window.innerWidth
  const windowHeight = window.innerHeight

  function plot (measurement, speakersName, speakersGraph) {
    // console.log('plot: ' + speakersName.length + ' names and ' + speakersGraph.length + ' graphs')
    async function run () {
      Promise.all(speakersGraph).then((graphs) => {
        // console.log('plot: resolved ' + graphs.length + ' graphs')
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
          }
          if (datasAndLayouts !== null && datasAndLayouts.length === 1 ) {
            let [datas, layout] = datasAndLayouts[0]
            if (datas !== null && layout !== null ) {
              Plotly.newPlot('plotDouble' + i, datas, layout, { responsive: true })
            }
          }
        }
        return null
      })
    }
    run()
  }

  function getNearSpeakers (metadata) {
    const metaSpeakers = {}
    const speakers = []
    metadata.forEach(function (value) {
      const speaker = value.brand + ' ' + value.model
      if (value.nearest && value.nearest.length > 0) {
        speakers.push(speaker)
        metaSpeakers[speaker] = value
      }
    })
    return [metaSpeakers, speakers.sort()]
  }

  function buildInitSpeakers (speakers) {
    if (urlParams.has('speaker0')) {
      const speaker0 = urlParams.get('speaker0')
      if (speaker0.length>3) {
        return speaker0
      }
    }
    return speakers[Math.floor(Math.random() * speakers.length)]
  }

  function updatePlots () {
    let speakerName = speakerSelector.value
    let graphName = graphSelector.value
    const names = []
    const graphs = []
    console.log('speaker >'+speakerName+'< graph >'+graphName+'<')
    graphs.push(
      getSpeakerData(
        metaSpeakers,
        graphName,
        speakerName,
        null,
        null
      ))
    names[0] = speakerName
    if (metaSpeakers[names[0]].nearest !== null ) {
      let similars = metaSpeakers[names[0]].nearest
      for( let i=0 ; i < similars.length ; i++ ) {
        // console.log('adding '+similars[i][1])
        names.push(similars[i][1])
        graphs.push(
          getSpeakerData(
            metaSpeakers,
            graphName,
            similars[i][1],
            null,
            null)
        )
      }
    }
    urlParams.set('measurement', graphName)
    urlParams.set('speaker0', speakerName)
    history.pushState(
      { page: 1 },
      'Change measurement',
      urlSimilar + urlParams.toString()
    )
    plot(graphName, names, graphs)
  }
  
  const [metaSpeakers, speakers] = getNearSpeakers(metadata);

  assignOptions(speakers, speakerSelector, buildInitSpeakers(speakers))
  assignOptions(knownMeasurements, graphSelector, knownMeasurements[0])

  // add listeners
  graphSelector.addEventListener('change', updatePlots, false)
  speakerSelector.addEventListener('change', updatePlots, false)

  updatePlots()

}).catch(err => console.log(err.message))
