#!/bin/sh
ssh-agent -k
eval `ssh-agent`
echo $SSH_AGENT_SOCK
if ! test -f ~/.ssh/id_rsa_github; then
    echo "github key don\'t exists!"
fi
github=$(ssh-add -l | grep github)
if test -z $github; then
    ssh-add ~/.ssh/id_rsa_github
    github=$(ssh-add -l | grep github)
else
    echo 'Github key already loaded'
fi    
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

echo 'SPIN          ' $SPIN
echo '  python3     ' $(python3 --version) $(which python3)
echo '  pip3        ' $(which pip3)
echo '  jupyter-lab ' $(which jupyter-lab)
echo '  PYTHONPATH  ' $PYTHONPATH
echo '  github key  ' $github
