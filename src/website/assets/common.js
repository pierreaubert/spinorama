// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

//@flow

import { urlSite } from './misc.js'
import { downloadZip } from './downloadzip.js'

export const knownMeasurements = [
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

function processOrigin (origin: string): string {
  if (origin.includes('Vendors-')) {
    return origin.slice(8)
  }
  return origin
}

function processGraph (name: string): string {
  if (name.includes('CEA2034')) {
    return 'CEA2034'
  } else if (name.includes('3D')) {
    return name.replace('3D', 'Contour')
  } else if (name.includes('Globe')) {
    return name.replace('Globe', 'Contour')
  }
  return name
}

type MetaSpeaker = {
    default_measurement: string,
    brand: string,
    model: string,
    tfgype: 'active' | 'passive',
    price: number,
    shape: 'bookshelves' | 'floorstander',
    amount: 'pair' | 'each',
    measurements: Array<{
      origin: 'ASR' | 'ErinsAudioCorner',
      format: 'klippel',
      review?: string,
      review_published?: 'string',
    }>,
}

type MetaSpeakers = {speaker: MetaSpeaker}

type Metadata = Array<MetaSpeaker>

function getOrigin (metaSpeakers: MetaSpeakers, speaker:string , origin: string): string {
  // console.log('getOrigin ' + speaker + ' origin=' + origin)
  if (origin == null || origin === '') {
    const defaultMeasurement = metaSpeakers[speaker].default_measurement
    const defaultOrigin = metaSpeakers[speaker].measurements[defaultMeasurement].origin
    // console.log('getOrigin default=' + defaultOrigin)
    return processOrigin(defaultOrigin)
  }
  return processOrigin(origin)
}

function getVersion (metaSpeakers: MetaSpeakers, speaker:string, origin: string, version:string): string {
  if (version == null || version === '') {
    const defaultVersion = metaSpeakers[speaker].default_measurement
    return defaultVersion
  }
  return version
}

function getSpeakerUrl (metaSpeakers: MetaSpeakers, graph: string, speaker:string, origin: string, version: string): string {
  // console.log('getSpeakerUrl ' + graph + ' speaker=' + speaker + ' origin=' + origin + ' version=' + version)
  const url =
        urlSite +
        'speakers/' +
        speaker + '/' +
        getOrigin(metaSpeakers, speaker, origin) + '/' +
        getVersion(metaSpeakers, speaker, origin, version) + '/' +
        processGraph(graph) + '.json.zip'
  return url
}

export function getSpeakerData (metaSpeakers: MetaSpeakers, graph: string, speaker:string, origin:string, version:string) : any | null {
    // console.log('getSpeakerData ' + graph + ' speaker=' + speaker + ' origin=' + origin + ' version=' + version)
    const url = getSpeakerUrl(metaSpeakers, graph, speaker, origin, version)
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

export function getAllSpeakers (metadata: Metadata) : Array<MetaSpeakers|Array<string>> {
  const metaSpeakers: MetaSpeakers = {}
  const speakers = []
  metadata.forEach( (value) => {
    const speaker = value.brand + ' ' + value.model
    speakers.push(speaker)
    metaSpeakers[speaker] = value
  })
  return [metaSpeakers, speakers.sort()]
}


export function getMetadata () {
  const url = urlSite+'assets/metadata.json.zip'
  // console.log('fetching url=' + url)
  const spec = downloadZip(url).then( function(zipped) {
    // convert to JSON
    // console.log('parsing url=' + url)
    const js = JSON.parse(zipped)
    // convert to object
    const metadata = Object.values(js)
    // console.log('metadata '+metadata.length)
    return metadata
  }).catch( (error) => {
    console.log('ERROR getMetadata data 404 ' + error)
    return null
  })
  return spec
}

type GraphLayout = ?{
  width: number,
  height: number,
  margin: number,
  legend: {
    orientation: string,
    x: number,
    y: number,
  },
  margin: {
    l: number,
    r: number,
    t: number,
    b: number,
  },
};

type GraphData = ?{
  data: any
};

type Graph = ?{
  data: GraphData,
  layout: GraphLayout,
}

type Graphs = Array<Graph>

function setGraphOptions (spin: Graphs, windowWidth: number, windowHeight: number) : Graphs {

  const graphSmall = 400
  const graphRatio = 1.414
  const graphMarginTop = 30
  const graphMarginBottom = 40
  const graphTitle = 30
  const graphSpacer = graphMarginTop + graphMarginBottom+graphTitle
  const graphExtraPadding = 40

  let datas = null
  let layout = null
  let config = null
  let countDifferent = 0
  // console.log('layout and data: ' + spin.length + ' w='+windowWidth+' h='+windowHeight)
  if (spin.length === 1) {
    layout = spin[0].layout
    datas = spin[0].data
  } else if (spin.length === 2 ) {
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
  }
  if (layout != null && datas != null) {
    if (windowWidth < graphSmall || windowHeight < graphSmall) {
      if (windowWidth < windowHeight ) {
        // portraint
        layout.width = windowWidth
        layout.height = Math.min(windowHeight, windowWidth / graphRatio + graphSpacer)
        // hide axis to recover some space on mobile
        layout.yaxis.visible = false
        if (layout.yaxis2) {
          layout.yaxis2.visible = false
        }
        layout.xaxis.title = 'SPL (dB) v.s. Frequency (Hz)'
      } else {
        // landscape
        layout.height = windowHeight + graphSpacer
        layout.width = Math.min(windowWidth, windowHeight*graphRatio+graphSpacer)
      }
      // get legend horizontal below the graph
      layout.margin = {
        l: 5,
        r: 0,
        t: graphMarginTop,
        b: graphMarginBottom,
      }
      layout.legend = {
        orientation: 'h',
        y: -0.25,
        x: 0,
        xanchor: 'bottom',
        yanchor: 'left'
      }
      // add a legend title to replace the legend group
      if( datas[0].legendgrouptitle ) {
        let title = datas[0].legendgrouptitle.text
        if (title) {
          for (let k = 1; k < datas.length; k++) {
            if (datas[k-1].legendgrouptitle.text != datas[k].legendgrouptitle.text ) {
              title += ' v.s.' + datas[k].legendgrouptitle.text
              countDifferent++
            }
          }
        }
        layout.title = {
          text: title,
          font: {
            size: 16,
            color: '#000',
          },
          xref: 'paper',
          x: 0.05
        }
      }
      // shorten labels
      for (let k = 0; k < datas.length; k++) {
        // remove group
        datas[k].legendgroup = null
        datas[k].legendgrouptitle = null
        if (datas[k].name && labelShort[datas[k].name]) {
          // shorten labels
          datas[k].name = labelShort[datas[k].name]
        }
      }
      // remove mod bar
      config = {
        responsive: true,
        displayModeBar: false,
      }
      layout.font = { size: 11 }
    } else {
      // larger screen
      layout.width = windowWidth - graphExtraPadding
      layout.height = Math.max(
        800,
        Math.min(
          windowHeight - graphExtraPadding,
          windowWidth / graphRatio + graphExtraPadding + graphSpacer)
      )
      layout.margin = {
        l: 15,
        r: 15,
        t: graphMarginTop*2,
        b: graphMarginBottom,
      }
      layout.legend = {
        orientation: 'h',
        y: -0.1,
        x: 0,
        xanchor: 'bottom',
        yanchor: 'left'
      }
      config = {
        responsive: true,
        displayModeBar: true,
      }
      if( datas[0].legendgrouptitle ) {
        let title = datas[0].legendgrouptitle.text
        if (title) {
          for (let k = 1; k < datas.length; k++) {
            if (datas[k-1].legendgrouptitle.text != datas[k].legendgrouptitle.text ) {
              title += ' v.s.' + datas[k].legendgrouptitle.text
              countDifferent++
            }
          }
        }
        layout.title = {
          text: title,
          font: {
            size: 18+windowWidth/300,
            color: '#000',
          },
          xref: 'paper',
          // title start sligthly on the right
          x: 0.05,
          // keep title below modBar if title is long
          y: 0.975,
        }
      }
      layout.font = { size: 11+windowWidth/300 }
    }
    if (layout.xaxis) {
      layout.xaxis.autotick = false
    }
    if (layout.yaxis) {
      layout.yaxis.dtick = 1
    }
    if (countDifferent === 0) {
      for (let k = 0; k < datas.length; k++) {
        datas[k].legendgroup = null
        datas[k].legendgrouptitle = null
      }
    }
  } else {
    // should be a pop up
    console.log('Error: No graph available')
  }
  return {'data': datas, 'layout': layout, 'config': config}
}

export function setCEA2034 (speakerNames: Array<string>, speakerGraphs: Graphs, width: number, height: number) : Array<LayoutData> {
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
  return [setGraphOptions(speakerGraphs, width, height)]
}

export function setGraph (speakerNames: Array<string>, speakerGraphs: Graphs, width: number, height:number) : Array<LayoutData> {
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
  return [setGraphOptions(speakerGraphs, width, height)]
}

export function setContour (speakerNames: Array<string>, speakerGraphs: Graphs, width: number, height:number)  : Array<LayoutData> {
  // console.log('setContour got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
  const graphsConfigs = []
  const config = {
    responsive: true,
    displayModeBar: true,
  }
  for (const i in speakerGraphs) {
    if (speakerGraphs[i]) {
      for (const j in speakerGraphs[i].data) {
        speakerGraphs[i].data[j].legendgroup = 'speaker' + i
        speakerGraphs[i].data[j].legendgrouptitle = { text: speakerNames[i] }
      }
      graphsConfigs.push({
        'data': speakerGraphs[i].data,
        'layout': speakerGraphs[i].layout,
        'config': config,
      })
    }
  }
  return graphsConfigs
}


export  function setGlobe (speakerNames: Array<string>, speakerGraphs: Graphs, width: number, height: number)  : Array<LayoutData> {
  // console.log('setGlobe ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
  const graphsConfigs = []
  const config = {
    responsive: true,
    displayModeBar: true,
  }
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
      let layout = speakerGraphs[i].layout
      layout.polar = {
        bargap: 0,
        hole: 0.05
      }
      graphsConfigs.push({
        'data': polarData,
        'layout': layout,
        'config': config,
      })
    }
  }
  return graphsConfigs
}

export function setSurface (speakerNames: Array<string>, speakerGraphs: Graphs, width: number, height: number)  : Array<LayoutData> {
  // console.log('setSurface ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
  const graphsConfigs = []
  const config = {
    responsive: true,
    displayModeBar: true,
  }
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
      layout.width = width
      layout.height = (height - 100) / 2
      layout.yaxis = {
        range: [-60, 60]
      }
      layout.zaxis = {
        range: [-20, 5]
      }
      graphsConfigs.push({
        'data': surfaceData,
        'layout': layout,
        'config': config,
      })
    }
  }
  return graphsConfigs
}

export function setCEA2034Split (speakerNames: Array<string>, speakerGraphs: Graphs, windowWidth: number, windowHeight: number)  : Array<LayoutData> {
  // console.log('setCEA2034Split got ' + speakerGraphs.length + ' graphs')
  const graphsConfigs = []
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
  const config = {
    responsive: true,
    displayModeBar: true,
  }

  if (speakerGraphs[0] != null && speakerGraphs[1] != null) {
    layout = speakerGraphs[0].layout
    datas = speakerGraphs[0].data.concat(speakerGraphs[1].data)

    layout.width = windowWidth - 40
    layout.height = Math.max(360, Math.min(windowHeight, windowWidth * 0.7 + 140))
    layout.title = null
    layout.font = { size: 12 }
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

    graphsConfigs.push({
      'data': datas,
      'layout': layout,
      'config': config,
    })

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

    graphsConfigs.push({
      'data': datas,
      'layout': layout2,
      'config': config,
    })
  } else {
    graphsConfigs.push(setGraphOptions(speakerGraphs, windowWidth, windowHeight))
  }
  return graphsConfigs
}

export function assignOptions (textArray: Array<string>, selector, textSelected: string) : null {
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

export function updateVersion (metaSpeakers: MetaSpeakers, speaker, selector, origin, value) {
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

export function updateOrigin (metaSpeakers: MetaSpeakers, speaker, originSelector, versionSelector, origin, version) {
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
  updateVersion(metaSpeakers, speaker, versionSelector, originSelector.value, version)
}
