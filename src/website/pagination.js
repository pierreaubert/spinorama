// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

/*eslint no-undef: "error"*/

import { urlParameters2Sort } from './search.js';

function urlChangePage(url, newpage) {
    const newUrl = new URL(url);
    newUrl.searchParams.set('page', newpage);
    return newUrl.toString();
}

export function pagination(numberSpeakers) {
    const navigationContainer = document.querySelector('#pagination');
    const navHeader = '<nav class="pagination" role="navigation" aria-label="pagination">';
    const navFooter = '</nav>';

    const url = new URL(window.location);
    const params = urlParameters2Sort(url);
    const currentPage = params[3].page;
    const perPage = params[3].count;
    const maxPage = Math.floor(numberSpeakers / perPage);
    const prevPage = Math.max(currentPage - 1, 1);
    const nextPage = Math.min(currentPage + 1, maxPage);

    // console.log('currentPage='+currentPage+' perPage='+perPage+' maxPage='+maxPage+' prevPage='+prevPage+' nextPage='+nextPage);

    if (numberSpeakers <= currentPage) {
	return;
    }

    let html = navHeader;
    if (currentPage <= 3) {
        let disabled = '';
        if (currentPage == 1) {
            disabled = ' is-disabled';
        }
        html += '<a href="' + urlChangePage(url, prevPage) + '" class="pagination-previous' + disabled + '">Prev</a>';
        html += '<a href=' + urlChangePage(url, nextPage) + ' class="pagination-next">Next</a>';
        html += '<ul class="pagination-list">';
        for (let i = 1; i <= Math.min(3, maxPage); i++) {
            let current = '';
            if (i === currentPage) {
                current = 'is-current';
            }
            html +=
                '<li><a href="' +
		urlChangePage(url, i) +
                ' class="pagination-link ' +
		current +
		'" aria-label="Goto page ' +
		i +
		'">' +
		i +
		'</a></li>';
        }
        if (maxPage > 5) {
            html += '<li><span class="pagination-ellipsis">&hellip;</span></li>';
            html +=
                '<li><a href="' +
                urlChangePage(url, maxPage) +
                '" class="pagination-link" aria-label="Goto page ' +
                maxPage +
                '">' +
                maxPage +
                '</a></li>';
        }
        html += '</ul>';
    } else if (maxPage - currentPage <= 3) {
        let disabled = '';
        if (currentPage == maxPage) {
            disabled = ' is-disabled';
        }
        html += '<a href="' + urlChangePage(url, prevPage) + '" class="pagination-previous">Prev</a>';
        html += '<a href=' + urlChangePage(url, nextPage) + ' class="pagination-next' + disabled + '">Next</a>';
        html += '<ul class="pagination-list">';
        if (maxPage > 5) {
            html += '<li><a href="' + urlChangePage(url, 1) + '" class="pagination-link" aria-label="Goto page 1">1</a></li>';
            html += '<li><span class="pagination-ellipsis">&hellip;</span></li>';
        }
        for (let i = Math.max(1, maxPage - 3); i <= maxPage; i++) {
            let current = '';
            if (i === currentPage) {
                current = 'is-current';
            }
            html +=
                '<li><a href="' +
                urlChangePage(url, i) +
                '" class="pagination-link ' +
                current +
                '" aria-label="Goto page ' +
                i +
                '">' +
                i +
                '</a></li>';
        }
        html += '</ul>';
    } else {
        html += '<a href="' + urlChangePage(url, prevPage) + '" class="pagination-previous">Prev</a>';
        html += '<a href=' + urlChangePage(url, nextPage) + ' class="pagination-next">Next</a>';
        html += '<ul class="pagination-list">';
        html += '<li><a href="' + urlChangePage(url, 1) + '" class="pagination-link" aria-label="Goto page 1">1</a></li>';
        html += '<li><span class="pagination-ellipsis">&hellip;</span></li>';
        for (let i = currentPage - 2; i <= currentPage + 2; i++) {
            let current = '';
            if (i === currentPage) {
                current = 'is-current';
            }
            if (i !== currentPage - 1 && i !== currentPage + 1) {
                html +=
                    '<li><a href="' +
                    urlChangePage(url, i) +
                    '" class="pagination-link ' +
                    current +
                    '" aria-label="Goto page ' +
                    i +
                    '">' +
                    i +
                    '</a></li>';
            }
        }
        html += '<li><span class="pagination-ellipsis">&hellip;</span></li>';
        html +=
            '<li><a href="' +
            urlChangePage(url, maxPage) +
            '" class="pagination-link" aria-label="Goto page ' +
            maxPage +
            '">' +
            maxPage +
            '</a></li>';
        html += '</ul>';
    }
    html += navFooter;
    const divNavigation = document.createElement('div');
    while (divNavigation.firstChild) {
        divNavigation.removeChild(divNavigation.firstChild);
    }
    divNavigation.innerHTML = html;
    navigationContainer.appendChild(divNavigation);
}
