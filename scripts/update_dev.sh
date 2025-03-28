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

# TARGET=$HOME/src/pierreaubert.github.io/spinorama
# TARGET=/var/www/html/spinorama-prod
# TARGET=/var/www/html/spinorama-dev
# TARGET=pierre@ch.spinorama.org:/var/www/html/spinorama-dev
# TARGET=pierre@es.spinorama.org:/var/www/html/spinorama-dev
# TARGET=pierre@web:/var/www/html/spinorama-dev
TARGET=pierre@192.168.1.18:/var/www/html/spinorama-dev
# check
command=$(grep www.spinorama.org dist/*.html | wc -l)
if [ $command -ne 0 ]; then
    echo "KO found prod url in dev site"
    exit 1;
else
    echo "OK checking for prod site in dev"
fi
command=$(grep spinorama.internet-box.ch dist/*.html | wc -l)
if [ $command -ne 0 ]; then
    echo "KO found old dev url in prod site"
    exit 1;
else
    echo "OK checking for dev site in prod"
fi
# copy
echo "Sync"
rsync -arvz --exclude '*.png' --delete ./dist/* "$TARGET"
rsync -arvz --include '*.png' --delete ./dist/pictures/* "$TARGET/pictures"

