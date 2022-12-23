import { setGraph } from './common.js'

export function displayGraph (divName, graphSpec) {
  async function run () {
    const w = window.innerWidth
    const h = window.innerHeight

    const title = graphSpec.layout.title.text
    const graphOptions = setGraph([title], [graphSpec], w, h)

    if (graphOptions && graphOptions.length >= 1) {
      Plotly.newPlot(divName, graphOptions[0])
    }
  }
  run()
}
