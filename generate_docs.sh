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

echo "Starting Generation"
export PYTHONPATH=src:.
rm -fr docs
rm -f cache.*.h5
mkdir docs docs/assets docs/pictures
# generates smaller pictures
./update_pictures.sh
# generates all graphs per speaker
python3 ./generate_graphs.py
# save some space and generates jpg from png
./update_pictures.sh
# all metadata (computed)
python3 ./generate_meta.py
# some stats for all speakers
python3 ./generate_stats.py
# static website generation
python3 ./generate_html.py
echo "Done"
