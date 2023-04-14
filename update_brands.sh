#!/bin/sh
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

export LOCALE=C
json_pp < docs/assets/metadata.json  | \
    grep '"brand" : ' | \
    cut -d: -f 2 | \
    cut -b 2- | \
    sed -e 's/[,"]//g' | \
    sort -s -V -f -u | \
    awk '{brand=$0; gsub("&", "&amp;", $0) ; printf("<option value=\"%s\">%s</option>\n", brand, $0);}' > src/website/brands.html
