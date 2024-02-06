#!/bin/sh

ubuntu-drivers devices

VERSION=545

apt install --reinstall nvidia-driver-${VERSION}
apt install linux-headers-$(uname -r)
apt --fix-broken install
apt install nvidia-dkms-${VERSION}

