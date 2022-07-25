#!/bin/sh

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

## python virtualenv
## ----------------------------------------------------------------------
SPIN=$PWD
export PYTHONPATH=$SPIN/src:$SPIN/src/website
if ! test -d $SPIN/spinorama-venv; then
    python3 -m venv spinorama-venv
    source $SPIN/spinorama-venv/bin/activate
    # rehash
    pip3 install -U pip
    pip3 install -r requirements.txt
    pip3 install -r requirements-tests.txt
    # currently not working on ubuntu-21.10
    # ray install-nightly
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
GPU=""
if test -x /usr/bin/nvidia-smi; then
    GPU=$(nvidia-smi  -L)
fi
if test -d /usr/local/cuda/extras/CUPTI/lib64; then
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/extras/CUPTI/lib64
fi

## summary
## ----------------------------------------------------------------------
echo 'SPIN          ' "$SPIN"
echo ' ' "$(python3 --version) $(which python3)"
echo ' ' "$(pip3 -V)"
echo '  jupyter-lab ' "$(jupyter-lab --version) $(which jupyter-lab)"
echo '  PYTHONPATH  ' "$PYTHONPATH"
echo '  github key  ' "$github"
echo '  GPU         ' "$GPU"
echo '  RAY         ' "$(ray --version)"
