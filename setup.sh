#!/bin/sh
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
pip3 install -r requirements.txt

# node section
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
nvm install lts/fermium
npm install vega-lite vega-cli canvas
npm install pyright html-validator-cli standard

# lint
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude spinorama-venv

# run the test
pip3 install -r requirements-tests.txt
pytest




