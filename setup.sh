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

## package check
## ----------------------------------------------------------------------

# apt install -y python3 python3-pip imagemagick keychain npm wget
# wget -O- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash

export PYTHONPATH=./src:./src/website
export NVM_DIR=$HOME/.nvm

# CUDA stuff for tensorflow
#
# wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
# sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
# sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/7fa2af80.pub
# sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /"
# sudo apt-get update
# sudo apt-get -y install nvidia-cuda nvidia-cuda-toolkit libcudnn8

# python section
python3 -m venv spinorama-venv
. ./spinorama-venv/bin/activate
pip3 install -U -r requirements.txt

# node section
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
# nvm install lts/fermium
npm install --save-dev pyright w3c-html-validator standard flow flow-remove-types

# lint
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude spinorama-venv

# compile
PYTHONPATH=src cd src/spinorama && python setup.py build_ext --inplace && ln -s c_compute_scores.cpython-*.so c_compute_scores.so && cd ../..

# install deepsource
[ ! -x bin/deepsource ] && curl https://deepsource.io/cli | sh

# run the test
pip3 install -U -r requirements-tests.txt
pip3 install -U -r requirements-dev.txt
pip3 install -U -r requirements-api.txt
pytest
