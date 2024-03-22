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

/*global Fuse*/
/*eslint no-undef: "error"*/

import { getMetadata } from './download${min}.js';
import { show, hide } from './misc${min}.js';
import { sortMetadata2, isFiltered, isSearch } from './sort${min}.js';

getMetadata()
    .then((metadata) => {
        const resultdiv = document.querySelector('div.searchresults');
        // this 2 are global variables
        let url = new URL(window.location);
        let keywords = document.querySelector('#searchInput').value;

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

        const fuse = new Fuse(
            // Fuse take a list not a map
            [...metadata].map((item) => ({ key: item[0], speaker: item[1] })),
            {
                isCaseSensitive: false,
                matchAllTokens: true,
                findAllMatches: true,
                minMatchCharLength: 2,
                keys: ['speaker.brand', 'speaker.model', 'speaker.type', 'speaker.shape'],
                treshhold: 0.2,
                distance: 10,
                includeScore: true,
                useExtendedSearch: false,
                shouldSort: true,
            }
        );
        function readUrl() {
            // read sort type
            if (url.searchParams.has('sort')) {
                const sortParams = url.searchParams.get('sort');
                sorter.by = sortParams;
            }
            if (url.searchParams.has('reverse')) {
                const sortOrder = url.searchParams.get('reverse');
                if (sortOrder === 'true') {
                    sorter.reverse = true;
                    document.querySelector('#sortReverse').checked = true;
                } else {
                    sorter.reverse = false;
                    document.querySelector('#sortReverse').checked = false;
                }
            } else {
                sorter.reverse = false;
            }
            // read filter type
            for (const filterName of Object.keys(filter)) {
                if (url.searchParams.has(filterName)) {
                    filter[filterName] = url.searchParams.get(filterName);
                }
            }
            // read search type
            if (url.searchParams.has('search')) {
                keywords = url.searchParams.get('search');
                document.querySelector('#searchInput').value = keywords;
            }
        }

        function updateUrl() {
            // update sort
            if (sorter.by !== '') {
                url.searchParams.set('sort', sorter.by);
            } else {
                url.searchParams.delete('sort');
            }
            if (sorter.reverse !== '') {
                url.searchParams.set('reverse', sorter.reverse);
            } else {
                url.searchParams.delete('reverse');
            }
            if (keywords !== '') {
                url.searchParams.set('search', keywords);
            } else {
                url.searchParams.delete('search');
            }
            // update filters
            for (const [filterName, filterValue] of Object.entries(filter)) {
                if (filterValue !== '') {
                    url.searchParams.set(filterName, filterValue);
                } else {
                    url.searchParams.delete(filterName);
                }
            }
            // keywords
            if (keywords !== '') {
                url.searchParams.set('search', keywords);
            } else {
                url.searchParams.delete('search');
            }
            // push
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
                // console.log('searching with keywords: '+keywords+' #matches: '+results.length);
                if (results.length > 0) {
                    // minScore
                    for (const spk in results) {
                        if (results[spk].score < minScore) {
                            minScore = results[spk].score;
                        }
                    }
                }
                results = new Map(results.map((obj) => [obj.item.key, obj]));
            }

            // use the sorted index to re-generate the divs.
            let stripeCounter = 0;
            sortedIndex.forEach((key) => {
                const speaker = metadata.get(key);
                const filterTest = isFiltered(speaker, filter);
                const searchTest = isSearch(key, results, minScore, keywords);
                if (speakerMap.has(key)) {
                    // console.log('key='+key+' map='+speakerMap.get(key)+' filterTest='+filterTest+' searchTest='+searchTest);
                    if (filterTest && searchTest) {
                        const child = speakerMap.get(key);
                        child.classList.remove('has-background-light');
                        child.classList.toggle('has-background-light', stripeCounter % 2 == 0);
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

        document.querySelector('#inputPriceMin').addEventListener('change', function () {
            filter.priceMin = this.value;
            updateUrl(url, keywords);
            selectDispatch();
        });

        document.querySelector('#inputPriceMax').addEventListener('change', function () {
            filter.priceMax = this.value;
            updateUrl(url, keywords);
            selectDispatch();
        });

        document.querySelector('#sortBy').addEventListener('change', function () {
            // swap reverse if it exists and if we keep the same ordering
            sorter.reverse = false;
            if (url.searchParams.has('reverse') && sorter.by === this.value) {
                const sortOrder = url.searchParams.get('reverse');
                if (sortOrder === 'false') {
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
        buttons.forEach((b) => {
            const sortButton = document.querySelector('#sort-' + b + '-button');
            if (sortButton !== null) {
                sortButton.addEventListener('click', () => {
                    // update sort by
                    sorter.by = b;
                    // swap reverse if it exists
                    sorter.reverse = false;
                    updateUrl(url, keywords);
                    selectDispatch();
                });
            }
        });

        // TODO: need to deal with other keys (backspace, delete, return, C-K)
        // can I get the key if I use a generic event like change?
        document.querySelector('#searchInput').addEventListener('keyup', function () {
            // warning: keyword is a global variable
            keywords = document.querySelector('#searchInput').value;
            updateUrl();
            if (keywords.length > 2) {
                selectDispatch();
            }
        });

        document.querySelector('#sortReverse').addEventListener('change', function () {
            const sortReverse = document.querySelector('#sortReverse').value;
            if (sortReverse) {
                sorter.reverse = !sorter.reverse;
                updateUrl();
                selectDispatch();
            }
        });

        // if we have a parameter to start with we need to resort
        if (url.searchParams.has('sort')) {
            selectDispatch();
        }

        return metadata;
    })
    .catch((err) => console.log(err.message));
