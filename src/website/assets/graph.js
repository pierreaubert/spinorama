import { setGraph } from './common.js'

export function displayGraph (divName, graphSpec) {

  async function run () {
    let w = window.innerWidth
    let h = window.innerHeight

    const title = graphSpec.layout.title.text
    let graphOptions = setGraph([title], [graphSpec], w, h)

    if( graphOptions && graphOptions.length >= 1 ) {
      Plotly.newPlot(divName, graphOptions[0])
    }
  }
  run()
}
