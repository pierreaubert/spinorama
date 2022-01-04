import { urlSite } from './misc.js'

const metadata = fetch(urlSite + 'assets/metadata.json').then(
    response => response.json()
).then(
    json => Object.values( json )
)

export default await metadata;
