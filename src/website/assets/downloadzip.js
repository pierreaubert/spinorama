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

/*global zip*/
/*eslint no-undef: "error"*/

// import {zip} from './zip.min.js'

export function downloadZip(url) {
    async function get(entry) {
        return entry.getData(new zip.TextWriter());
    }

    async function download(url) {
        // console.log(`dowload start`);
        const cblob = new zip.HttpReader(url);
        const czip = new zip.ZipReader(cblob);
        const entries = await czip.getEntries();
        if (entries && entries.length) {
            // console.log(`found ${entries.length} ${entries[0].filename}`);
            const text = await get(entries[0]);
            return text;
        }
        return '{}';
    }

    return download(url);
}
