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

## package check
## ----------------------------------------------------------------------

OS=$(uname)
PYVERSION=3.12

if test "$OS" = "Linux"; then
  # ------------ PYTHON
  sudo [ -x /usr/bin/apt ] && /usr/bin/apt install -y python3 python3-pip imagemagick keychain npm wget python${PYVERSION}-venv
  # ------------ LOCALE
  # add locale if they don't exist possibly C.utf8 would work
  sudo [ -x /usr/bin/localedef ] && /usr/bin/localedef -f UTF-8 -i en_US en_US.UTF-8
  # or maybe
  # sudo apt -y install language-pack-en-base && localectl set-locale LANG=en_US.UTF-8
elif test "$OS" = "Darwin"; then
    brew install npm hdf5 c-blosc lzo bzip2 python@${PYVERSION} freetype imagemagick gawk gsed redis chromedriver
    xattr -d com.apple.quarantine $(which chromedriver)
    chmod 755 $(which chromedriver)
    export HDF5_DIR="$(brew --prefix hdf5)"
fi

export PYTHONPATH=./src:./src/website

# python section
python${PYVERSION} -m venv .venv
source ./.venv/bin/activate

ARCH=$(uname -a | awk '{print $NF}')
if test "$OS" = "Darwin"  -a "$ARCH" = "arm64" ; then
    # ack to install tables on arm
    echo pip install git+https://github.com/PyTables/PyTables.git@master#egg=tables
fi
pip3 install -U -r requirements.txt
pip3 install -U -r requirements-test.txt
pip3 install -U -r requirements-dev.txt
pip3 install -U -r requirements-api.txt

# update pip to prevent extra warning
pip install -U pip

# node section
npm install .

# lint
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude .venv

# compile
rm -f src/spinorama/c_compute_scores.cpython-*.so
PYTHONPATH=src cd src/spinorama && python3 setup.py build_ext --inplace && ln -s c_compute_scores.cpython-*.so c_compute_scores.so && cd ../..

# install deepsource
[ ! -x bin/deepsource ] && curl https://deepsource.io/cli | sh

# install 3rd parties
./scripts/update_3rdparties.sh
