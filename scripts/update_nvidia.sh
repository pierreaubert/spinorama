#!/bin/sh

ubuntu-drivers devices

VERSION=550

apt install --reinstall nvidia-driver-${VERSION}
apt install linux-headers-$(uname -r)
apt --fix-broken install
apt install nvidia-dkms-${VERSION}

candidates=$(ls -d /usr/src/nvidia-$VERSION.*)
numbers=$(basename $candidates)
sudo dkms install -m ${numbers/-/\/}
