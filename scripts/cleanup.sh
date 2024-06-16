# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

# various cache files
rm -fr .sass-cache
# node stuff
rm -fr ./node_modules
# emacs stuff
rm -f ./TAGS ./*/*/TAGS
rm -f .*~ */*~ */*/*~
rm -f \.#*\# \#.*\# *.md.tmp \#*\#
# python venv
rm -fr spinorama-venv venv .venv
rm -fr *.pyc src/*/*.pyc
rm -fr ./.ipynb_checkpoints
rm -fr ./__pycache__ ./*/__pycache__ ./*/*/__pycache__
rm -fr ./.pytest_cache ./*/.pytest_cache ./*/*/.pytest_cache
rm -fr ./.mypy_cache ./*/.mypy_cache ./*/*/.mypy_cache
rm -fr .ruff_cache
rm -f .coverage coverage.xml
rm -fr coverage
# latex stuff
rm -fr ./book/.pytest_cache ./book/*.aux ./book/*.bbl ./book/*.blg ./book/*.lof ./book/*.out ./book/*.pdf ./book/*.toc ./book/*.back ./book/tmp ./book/*~
# Mac stuff
rm -fr .DS_Store
# cpython stuff
rm -f src/spinorama/c_compute_scores.c
rm -f src/spinorama/c_compute_scores.so
rm -f src/spinorama/c_compute_scores.*.so
rm -f src/spinorama/c_compute_scores.*~
# spinorama
rm -fr ./.cache
rm -fr ./docs
rm -fr ./build
rm -f *.log */*.log
rm -fr /tmp/ray
rm -fr **/results_*.csv

