#!/bin/sh

ubuntu-drivers devices

VERSION=550

apt install --reinstall nvidia-driver-${VERSION}
apt install linux-headers-$(uname -r)
apt --fix-broken install
apt install nvidia-dkms-${VERSION}

sudo dkms install -m nvidia/545.29.06


