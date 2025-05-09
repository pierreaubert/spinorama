#!/bin/sh
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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

# TARGET1=pierre@ch.spinorama.org:/var/www/html/spinorama-prod
TARGET3=pierre@192.168.1.18:/var/www/html/spinorama-prod
TARGET4=pierre@192.168.1.20:/var/www/html/spinorama-prod

# check
command=$(grep dev.spinorama.org dist/*.html | wc -l)
if [ "${command}" -ne 0 ]; then
    echo "KO found DEV url in PROD site"
    exit 1;
else
    echo "OK checking for DEV site in PROD"
fi
command=$(grep spinorama.internet-box.ch dist/*.html | wc -l)
if [ "${command}" -ne 0 ]; then
    echo "KO found old dev url in prod site"
    exit 1;
else
    echo "OK checking for dev site in prod"
fi

# copy
echo "Sync starts:"
for target in "$TARGET3" "$TARGET4"; do
    rsync -avrz --exclude '*.png' --delete ./dist/* "$target"
    rsync -arvz --include '*.png' --delete ./dist/pictures/* "$target/pictures"
done
