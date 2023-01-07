#!/bin/sh
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
TARGET=/var/www/html/spinorama-dev
# check
command=$(grep dev.spinorama.org docs/*.html | wc -l)
if [ $command -ne 0 ]; then
    echo "KO found dev url in prod site"
    exit 1;
else
    echo "OK checking for dev site in prod"
fi
command=$(grep spinorama.internet-box.ch docs/*.html | wc -l)
if [ $command -ne 0 ]; then
    echo "KO found old dev url in prod site"
    exit 1;
else
    echo "OK checking for dev site in prod"
fi
# copy
echo "Sync"
rsync -arv --exclude '*.png' --delete ./docs/* $TARGET
rsync -arv --include '*.png' --delete ./docs/pictures/* $TARGET/pictures
rsync -arv --include '*.png' --delete ./docs/help_pictures/* $TARGET/help_pictures
#
find $TARGET/speakers -type f -name '*.png' -exec rm {} \;
