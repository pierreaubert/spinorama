#!/bin/sh

touch env.log

## package check
## ----------------------------------------------------------------------
# apt install -y python3 python3-pip imagemagick keychain npm
# npm install vega-lite vega-cli canvas
# wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
# sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
# sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/7fa2af80.pub
# sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /"
# sudo apt-get update
# sudo apt-get -y install nvidia-cuda nvidia-cuda-toolkit libcudnn8

## SSH AGENT
## ----------------------------------------------------------------------
ssh-agent -k 2>&1 >> env.log
eval `ssh-agent`
echo $SSH_AGENT_SOCK
if ! test -f ~/.ssh/id_rsa_github; then
    echo "ERROR github key don\'t exists!"
fi

## Github keys
## ----------------------------------------------------------------------
github=$(ssh-add -l | grep github)
if test -z $github; then
    ssh-add ~/.ssh/id_rsa_github 2>&1 >> env.log
    github=$(ssh-add -l 2>&1 | grep github)
fi

## python virtualenv
## ----------------------------------------------------------------------
SPIN=$HOME/src/spinorama
export PYTHONPATH=$SPIN/src
if ! test -d $SPIN/spinorama-venv; then
    python3 -m venv spinorama-venv
    rehash
    pip3 install -U pip
    pip3 install -r requirements.txt
    pip3 install -r requirements-tests.txt
    ray install ray-nightly
fi    
source $SPIN/spinorama-venv/bin/activate

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
echo 'SPIN          ' $SPIN
echo '  python3     ' $(python3 --version) $(which python3)
echo '  pip3        ' $(which pip3)
echo '  jupyter-lab ' $(which jupyter-lab)
echo '  PYTHONPATH  ' $PYTHONPATH
echo '  github key  ' $github
echo '  GPU         ' $GPU
echo '  RAY         ' $(ray --version)