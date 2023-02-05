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

import { getMetadata } from './common.js';
import { show, hide } from './misc.js';
import { sortMetadata2 } from './sort.js';

function isFiltered(item, filter) {
    let shouldShow = true;
    if (filter.reviewer !== undefined && filter.reviewer !== '') {
        let found = true;
        for (const [name, measurement] of Object.entries(item.measurements)) {
            const origin = measurement.origin.toLowerCase();
            let name2 = name.toLowerCase();
            // not ideal
            name2 = name2
                .replace('misc-', '')
                .replace('-sealed', '')
                .replace('-ported', '')
                .replace('-vertical')
                .replace('-horizontal');
            // console.log('debug: name2=' + name2 + ' origin=' + origin + ' filter.reviewer=' + filter.reviewer)
            if (name2 === filter.reviewer.toLowerCase() || origin === filter.reviewer.toLowerCase()) {
                found = false;
                break;
            }
        }
        if (found) {
            shouldShow = false;
        }
    }
    if (filter.quality !== undefined && filter.quality !== '') {
        let found = true;
        for (const [name, measurement] of Object.entries(item.measurements)) {
            const quality = measurement.quality.toLowerCase();
            // console.log('filter.quality=' + filter.quality + ' quality=' + quality)
            if (filter.quality !== '' && quality === filter.quality.toLowerCase()) {
                found = false;
                break;
            }
        }
        if (found) {
            shouldShow = false;
        }
    }
    // console.log('debug: post quality ' + shouldShow)
    if (filter.power !== undefined && filter.power !== '' && item.type !== filter.power) {
        shouldShow = false;
    }
    // console.log('debug: post power ' + shouldShow)
    if (filter.shape !== undefined && filter.shape !== '' && item.shape !== filter.shape) {
        shouldShow = false;
    }
    // console.log('debug: post shape ' + shouldShow)
    if (filter.brand !== undefined && filter.brand !== '' && item.brand.toLowerCase() !== filter.brand.toLowerCase()) {
        shouldShow = false;
    }
    // console.log('debug: post brand ' + shouldShow + 'filter.price=>>>'+filter.price+'<<<')
    if (filter.price !== undefined && filter.price !== '') {
        // console.log('debug: pre price ' + filter.price)
        if (item.price !== '') {
            let price = parseInt(item.price);
            if (item.amount === 'pair') {
                price /= 2.0;
            }
            switch (filter.price) {
                case 'p100':
                    if (price >= 100) {
                        shouldShow = false;
                    }
                    break;
                case 'p200':
                    if (price >= 200 || price <= 100) {
                        shouldShow = false;
                    }
                    break;
                case 'p300':
                    if (price >= 300 || price <= 200) {
                        shouldShow = false;
                    }
                    break;
                case 'p500':
                    if (price >= 500 || price <= 300) {
                        shouldShow = false;
                    }
                    break;
                case 'p1000':
                    if (price >= 1000 || price <= 500) {
                        shouldShow = false;
                    }
                    break;
                case 'p2000':
                    if (price >= 2000 || price <= 1000) {
                        shouldShow = false;
                    }
                    break;
                case 'p5000':
                    if (price >= 5000 || price <= 2000) {
                        shouldShow = false;
                    }
                    break;
                case 'p5000p':
                    if (price <= 5000) {
                        shouldShow = false;
                    }
                    break;
            }
        } else {
            // no known price
            shouldShow = false;
        }
        // console.log('debug: post price ' + shouldShow)
    }
    return shouldShow;
}

function isSearch(key, results, minScore, keywords) {
    let shouldShow = true;
    if (keywords === '' || results === undefined) {
        return shouldShow;
    }

    const result = results[key];
    const imeta = result.item;
    const score = result.score;

    if (minScore < Math.pow(10, -15)) {
        const isExact = imeta.model.toLowerCase().includes(keywords.toLowerCase());
        // console.log('isExact ' + isExact + ' model' + imeta.model.toLowerCase() + ' keywords ' + keywords.toLowerCase());
        // we have an exact match, only shouldShow other exact matches
        if (score >= Math.pow(10, -15) && !isExact) {
            // console.log('filtered out (minscore)' + score);
            shouldShow = false;
        }
    } else {
        // only partial match
        if (score > minScore * 10) {
            // console.log('filtered out (score=' + score + 'minscore=' + minScore + ')');
            shouldShow = false;
        }
    }
    return shouldShow;
}

getMetadata()
    .then((metadata) => {
        const url = new URL(window.location);
        const resultdiv = document.querySelector('div.searchresults');
        const keywords = document.querySelector('#searchInput').value;

        const filter = {
            brand: '',
            power: '',
            quality: '',
            price: '',
            reviewer: '',
            shape: '',
        };

        const sorter = {
            by: 'date',
            reverse: false,
        };

        function readUrl() {
            if (url.searchParams.has('sort')) {
                const sortParams = url.searchParams.get('sort');
            }
            if (url.searchParams.has('reverse')) {
                const sortOrder = url.searchParams.get('reverse');
                if (sortOrder === 'true' ) {
                    sorter.reverse = true;
                } else {
                    sorter.reverse = false;
                }
            } else {
                sorter.reverse = false;
            }
        }

        function updateUrl() {
            // update URL
            url.searchParams.set('sort', sorter.by);
            url.searchParams.set('reverse', sorter.reverse);
            if (keywords !== '') {
                url.searchParams.set('search', keywords);
            }
            window.history.pushState({}, '', url);
        }

        function selectDispatch() {
            readUrl();

            // sort first
            const sortedIndex = sortMetadata2(metadata, sorter);

            // regenerate the speakers section
            const speakerContainer = document.querySelector('[data-num="0"');
            const speakerDiv = [...speakerContainer.querySelectorAll('.searchable')];
            const speakerMap = new Map(speakerDiv.map((s) => [s.getAttribute('id'), s]));
            const fragment = new DocumentFragment();

            // do we have an exact match?
            let results;
            let minScore = 1;
            if (keywords !== '') {
                results = fuse.search(keywords);
                if (results.length > 0) {
                    // minScore
                    for (const spk in results) {
                        if (results[spk].score < minScore) {
                            minScore = results[spk].score;
                        }
                    }
                }
            }

            // use the sorted index to re-generate the divs.
            let stripeCounter = 0
            sortedIndex.forEach((key, index) => {
                const speaker = metadata.get(key);
                const filterTest = isFiltered(speaker, filter);
                const searchTest = isSearch(key, results, minScore, keywords);
                if (speakerMap.has(key)) {
                    // console.log('key='+key+' map='+speakerMap.get(key));
                    if (filterTest && searchTest) {
                        let child = speakerMap.get(key);
                        child.classList.remove('has-background-light');
                        child.classList.toggle('has-background-light', stripeCounter %2 == 0 );
                        show(fragment.appendChild(child));
                        stripeCounter = stripeCounter + 1;
                    } else {
                        hide(fragment.appendChild(speakerMap.get(key)));
                    }
                }
            });
            speakerContainer.appendChild(fragment);

            // show the whole div
            show(resultdiv);
        }

        document.querySelector('#selectReviewer').addEventListener('change', function () {
            filter.reviewer = this.value;
            updateUrl(url, keywords);
            selectDispatch();
        });

        document.querySelector('#selectQuality').addEventListener('change', function () {
            filter.quality = this.value;
            updateUrl(url, keywords);
            selectDispatch();
        });

        document.querySelector('#selectShape').addEventListener('change', function () {
            filter.shape = this.value;
            updateUrl(url, keywords);
            selectDispatch();
        });

        document.querySelector('#selectPower').addEventListener('change', function () {
            filter.power = this.value;
            updateUrl(url, keywords);
            selectDispatch();
        });

        document.querySelector('#selectBrand').addEventListener('change', function () {
            filter.brand = this.value;
            updateUrl(url, keywords);
            selectDispatch();
        });

        document.querySelector('#selectPrice').addEventListener('change', function () {
            filter.price = this.value;
            updateUrl(url, keywords);
            selectDispatch();
        });

        document.querySelector('#sortBy').addEventListener('change', function () {
            // swap reverse if it exists and if we keep the same ordering
            sorter.reverse = false;
            if (url.searchParams.has('reverse') && sorter.by === this.value ) {
                const sortOrder = url.searchParams.get('reverse');
                if (sortOrder === 'false' ) {
                    sorter.reverse = true;
                }
            }
            sorter.by = this.value;
            updateUrl(url, keywords);
            selectDispatch();
        });

        const buttons = [
            'brand',
            // 'date',
            'price',
            'f3',
            // 'f6',
            'flatness',
            'score',
            'scoreEQ',
            'scoreWSUB',
            'scoreEQWSUB',
        ];
        buttons.forEach(  b => {
            const sortButton = document.querySelector('#sort-' + b + '-button');
            if (sortButton !== null ) {
                sortButton.addEventListener('click', (e) => {
                    // update sort by
                    sorter.by = b;
                    // swap reverse if it exists
                    sorter.reverse = false;
                    if (url.searchParams.has('reverse')) {
                        const sortOrder = url.searchParams.get('reverse');
                        if (sortOrder === 'false' ) {
                            sorter.reverse = true;
                        }
                    }
                    updateUrl(url, keywords);
                    selectDispatch();
                });
            }
        });

        document.querySelector('#searchInput').addEventListener('keyup', function () {
            updateUrl(url, keywords);
            selectDispatch();
        });

        const fuse = new Fuse(metadata, {
            isCaseSensitive: false,
            matchAllTokens: true,
            findAllMatches: true,
            minMatchCharLength: 2,
            keys: ['brand', 'model'],
            treshhold: 0.5,
            distance: 4,
            includeScore: true,
            useExatendedSearch: true,
        });

        // if we have a parameter to start with we need to resort
        if (url.searchParams.has('sort')) {
            selectDispatch();
        }
    })
    .catch((err) => console.log(err.message));
