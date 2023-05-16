#!/bin/bash
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

echo "Update starts"
export PYTHONPATH=src:src/website:src/spinorama:.

DIST=/var/www/html/spinorama-api

cp ./scripts/gunicorn_start.sh $DIST
cp requirements-api.txt $DIST
cp datas/metadata.py $DIST/datas
cp docs/assets/metadata.json $DIST/datas
for source in "__init__.py" "main.py" "ai-plugin.json"; do
    cp ./src/api/$source $DIST;
done

cd $DIST && source .venv/bin/activate && pip install -U -r requirements-api.txt

echo "you may need to restart gunicorn and possibly reload nginx:"
echo "sudo supervisorctl restart spinorama-api"
echo "sudo nginx -s reload"

exit 0;
