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


touch env.log

## SSH AGENT
## ----------------------------------------------------------------------
ssh-agent -k >> env.log 2>&1
eval `ssh-agent`
echo $SSH_AGENT_SOCK
if ! test -f ~/.ssh/id_rsa_github; then
    echo "ERROR github key don\'t exists!"
fi

## Github keys
## ----------------------------------------------------------------------
github=$(ssh-add -l | grep github | cut -d ' ' -f 3)
if test -z $github; then
    ssh-add ~/.ssh/id_rsa_github >> env.log 2>&1
    github=$(ssh-add -l 2>&1 | grep github | cut -d ' ' -f 3)
fi

## prod keys
## ----------------------------------------------------------------------
RSA_ES=$HOME/.ssh/id_rsa_es_web
if test -f $RSA_ES; then
    ssh-add $RSA_ES >> env.log 2>&1
fi
RSA_CH=$HOME/.ssh/id_rsa_ch_web
if test -f $RSA_CH; then
    ssh-add $RSA_CH >> env.log 2>&1
fi

## python virtualenv
## ----------------------------------------------------------------------
SPIN=$PWD
export PYTHONPATH=$SPIN/src:$SPIN/src/website:$SPIN
if ! test -d $SPIN/spinorama-venv; then
    python3 -m venv spinorama-venv
    source $SPIN/spinorama-venv/bin/activate
    # rehash
    pip3 install -U pip
    pip3 install -r requirements.txt
    pip3 install -r requirements-test.txt
    pip3 install -r requirements-dev.txt
fi
source $SPIN/spinorama-venv/bin/activate

## node install
## ----------------------------------------------------------------------
if ! test -d $SPIN/node_modules; then
    npm install plotly
    npm install pyright html-validator-cli standard flow-remove-types
fi
export PATH=$PATH:$SPIN/node_modules/.bin

## CUDA configuration
## ----------------------------------------------------------------------
CUDA=""
if test -x /usr/bin/nvidia-smi; then
    CUDA=$(nvidia-smi  -L)
fi
if test -d /usr/local/cuda/extras/CUPTI/lib64; then
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/extras/CUPTI/lib64
fi

## ROCM/HIP configuration
## ----------------------------------------------------------------------
ROCM=""
if test -x /usr/bin/rocminfo; then
    ROCM=$(rocminfo  | grep 'Marketing Name' | grep Radeon | cut -d: -f 2 | sed -e 's/  //g')
fi
if test -d /usr/local/cuda/extras/CUPTI/lib64; then
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/extras/CUPTI/lib64
fi

# for deepsource code coverage
export DEEPSOURCE_DSN=https://sampledsn@deepsource.io

## summary
## ----------------------------------------------------------------------
echo 'SPIN           ' "$SPIN"
echo ' ' "$(python3 --version) $(which python3)"
echo ' ' "$(pip3 -V) "
echo '  jupyter-lab  ' "$(jupyter-lab --version) $(which jupyter-lab)"
echo '  PYTHONPATH   ' "$PYTHONPATH"
echo '  github key   ' "$github"
echo '  CUDA (Nvidia)' "$CUDA"
echo '  ROCM (AMD)   ' "$ROCM"
echo '  RAY          ' "$(ray --version)"
