#!/bin/sh
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

## package check
## ----------------------------------------------------------------------

OS=$(uname)

if test "$OS" = "Linux"; then
  # ------------ PYTHON
  sudo [ -x /usr/bin/apt ] && /usr/bin/apt install -y python3 python3-pip imagemagick keychain npm wget python3.11-venv
  # ------------ LOCALE
  # add locale if they don't exist possibly C.utf8 would work
  sudo [ -x /usr/bin/localedef ] && /usr/bin/localedef -f UTF-8 -i en_US en_US.UTF-8
  # or maybe
  # sudo apt -y install language-pack-en-base && localectl set-locale LANG=en_US.UTF-8
  # ------------ NPM
  # should not be required
  # wget -O- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash
  # ------------ CUDA stuff for tensorflow
  # wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
  # sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
  # sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/7fa2af80.pub
  # sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /"
  # sudo apt-get update
  # sudo apt-get -y install nvidia-cuda nvidia-cuda-toolkit libcudnn8
elif test "$OS" = "Darwin"; then
  brew install npm hdf5 c-blosc lzo bzip2 python@3.10 freetype imagemagick gawk gsed
  export HDF5_DIR="$(brew --prefix hdf5)"
fi

export PYTHONPATH=./src:./src/website
export NVM_DIR=$HOME/.nvm

# python section
python3 -m venv .venv
. ./.venv/bin/activate
ARCH=$(uname -a | awk '{print $NF}')
if test "$OS" = "Darwin"  -a "$ARCH" = "arm64" ; then
    # ack to install tables on arm
    echo pip install git+https://github.com/PyTables/PyTables.git@master#egg=tables
fi
pip3 install -U -r requirements.txt
pip3 install -U -r requirements-test.txt
pip3 install -U -r requirements-dev.txt
pip3 install -U -r requirements-api.txt

# node section
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
npm install --save-dev pyright w3c-html-validator standard flow flow-remove-types critical terser

# lint
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude .venv

# compile
PYTHONPATH=src cd src/spinorama && python setup.py build_ext --inplace && ln -s c_compute_scores.cpython-*.so c_compute_scores.so && cd ../..

# install deepsource
[ ! -x bin/deepsource ] && curl https://deepsource.io/cli | sh

# run the test
pytest tests
