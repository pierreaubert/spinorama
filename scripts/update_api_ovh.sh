#!/bin/bash
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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

echo "Update starts"
export PYTHONPATH=src:src/website:src/spinorama:.

DIST=/var/www/html/spinorama-api
TARGET=spin@vps-c2ea73ea.vps.ovh.net:$DIST

rsync -arv ./scripts/gunicorn_start.sh requirements-api.txt $TARGET
rsync -arv ./datas/*.py $TARGET/datas
rsync -arv ./dist/json/metadata.json* $TARGET/assets
rsync ./src/api/__init__.py ./src/api/main.py $TARGET
rsync ./conf/etc/supervisor/conf.d/spinorama-app.conf $TARGET/etc

echo "1. as spin user"
echo "cd $DIST && python3 -m venv .venv && source .venv/bin/activate && pip install -U -r requirements-api.txt"

echo "2. you may need to restart gunicorn and possibly reload nginx:"
echo "sudo cp $DIST/etc/spinorama-app.conf /etc/supervisor/conf.d/"
echo "sudo supervisorctl restart spinorama-api"
echo "sudo nginx -s reload"

exit 0;
