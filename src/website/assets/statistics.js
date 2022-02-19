// import { Plotly } from '../../../node_modules/plotly/index.js'
import { urlSite } from './misc.js'

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.json()
  }).then((dataJson) => {
  const metadata = Object.values(dataJson)
  const windowWidth = window.innerWidth

  function plotScoreDistribution (scores, scoresEQ) {
    const traceScores = {
      x: scores,
      type: 'histogram',
      opacity: 0.5,
      marker: {
        color: 'blue'
      },
      name: 'Score'
    }
    const traceScoresEQ = {
      x: scoresEQ,
      type: 'histogram',
      opacity: 0.5,
      marker: {
        color: 'orange'
      },
      name: 'Score w/EQ'
    }
    const data = [traceScores, traceScoresEQ]
    const layout = {
      width: Math.max(400, Math.min(600, windowWidth)),
      title: { text: 'Distribution of scores' },
      xaxis: {
        title: 'Score',
        range: [0, 10]
      },
      yaxis: { title: 'Count' },
      barmode: 'overlay',
      legend: {
        orientation: 'h',
        y: -0.3
      }
    }
    Plotly.newPlot('visScoreDistribution', data, layout)
  }

  function plotScoreDistributionWsub (scores, scoresEQ) {
    const traceScores = {
      x: scores,
      type: 'histogram',
      opacity: 0.5,
      marker: {
        color: 'blue'
      },
      name: 'Score w/Sub'
    }
    const traceScoresEQ = {
      x: scoresEQ,
      type: 'histogram',
      opacity: 0.5,
      marker: {
        color: 'orange'
      },
      name: 'Score w/Sub+w/EQ'
    }
    const data = [traceScores, traceScoresEQ]
    const layout = {
      width: Math.max(400, Math.min(600, windowWidth)),
      title: { text: 'Distribution of scores with a perfect subwoofer' },
      xaxis: {
        title: 'Score',
        range: [0, 10]
      },
      yaxis: {
        title: 'Count'
      },
      barmode: 'overlay',
      legend: {
        orientation: 'h',
        y: -0.3
      }
    }
    Plotly.newPlot('visScoreDistributionWsub', data, layout)
  }

  function plotParameters (name, title, param, scores, names, divname) {
    const trace = {
      x: scores,
      y: param,
      mode: 'markers',
      type: 'scatter',
      name: name,
      text: names
    }
    const data = [trace]
    const layout = {
      width: Math.max(400, Math.min(800, windowWidth)),
      title: { text: title },
      legend: {
        orientation: 'h',
        y: -0.3
      },
      xaxis: {
        title: 'Score'
      },
      yaxis: {
        title: name
      }
    }
    Plotly.newPlot(divname, data, layout)
  }

  function stats () {
    const scores = []
    const scoresEQ = []
    const scoresWsub = []
    const scoresWsubEQ = []
    const lfx = []
    const nbdON = []
    const nbdPIR = []
    const smPIR = []
    const names = []
    metadata.forEach((value, key) => {
      if (value.measurements &&
                    value.measurements[value.default_measurement].pref_rating &&
                    value.measurements[value.default_measurement].pref_rating.pref_score) {
      // gather various scores
        scores.push(value.measurements[value.default_measurement].pref_rating.pref_score)
        scoresEQ.push(value.measurements[value.default_measurement].pref_rating_eq.pref_score)
        scoresWsub.push(value.measurements[value.default_measurement].pref_rating.pref_score_wsub)
        scoresWsubEQ.push(value.measurements[value.default_measurement].pref_rating_eq.pref_score_wsub)
        // components of the score
        lfx.push(value.measurements[value.default_measurement].pref_rating.lfx_hz)
        nbdON.push(value.measurements[value.default_measurement].pref_rating.nbd_on_axis)
        nbdPIR.push(value.measurements[value.default_measurement].pref_rating.nbd_pred_in_room)
        smPIR.push(value.measurements[value.default_measurement].pref_rating.sm_pred_in_room)
        //
        names.push(value.brand + ' ' + value.model)
      }
    })
    // console.log('found ' + scores.length + ' scores')
    plotScoreDistribution(scores, scoresEQ)
    plotScoreDistributionWsub(scoresWsub, scoresWsubEQ)
    plotParameters('LFX (Hz)', 'Low Frequency eXtension (LFX) v.s. Score', lfx, scores, names, 'visDistributionLfxHz')
    plotParameters('NBD ON', 'Narrow Bandwidth On Axis (NBD ON) v.s. Score', nbdON, scores, names, 'visDistributionNbdOn')
    plotParameters('NBD PIR', 'Narrow Bandwidth Predicted In Room (NBD PIR) v.s. Score', nbdPIR, scores, names, 'visDistributionNbdPir')
    plotParameters('SM PIR', 'Smoothness Predicted In Room (SM PIR) v.s. Score', smPIR, scores, names, 'visDistributionSmPir')
  }

  stats()
}).catch(err => console.log(err.message))
