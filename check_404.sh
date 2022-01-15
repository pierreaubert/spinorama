#!/bin/bash

pylinkvalidate.py -P http://spinorama.internet-box.ch

for f in docs/speakers/*/*/*/*.html; do
    name=${f#docs/}
    u=${name// /%20}
    pylinkvalidate.py -P "http://spinorama.internet-box.ch/$u"
done
