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

export function urlParameters2Sort(url) {
    let keywords = '';
    const filter = {
        brand: '',
        power: '',
        quality: '',
        priceMin: '',
        priceMax: '',
        reviewer: '',
        shape: '',
    };
    const sorter = {
        by: 'date',
        reverse: false,
    };

    if (url.searchParams.has('sort')) {
        const sortParams = url.searchParams.get('sort');
        sorter.by = sortParams;
    }
    if (url.searchParams.has('reverse')) {
        const sortOrder = url.searchParams.get('reverse');
        if (sortOrder === 'true') {
            sorter.reverse = true;
        } else {
            sorter.reverse = false;
        }
    } else {
        sorter.reverse = false;
    }
    for (const filterName of Object.keys(filter)) {
        if (url.searchParams.has(filterName)) {
            filter[filterName] = url.searchParams.get(filterName);
        }
    }
    if (url.searchParams.has('search')) {
        keywords = url.searchParams.get('search');
    }
    return [sorter, filter, keywords];
}
