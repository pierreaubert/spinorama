#!/bin/bash

TARGET=/var/www/html/spinorama-api

cp ./datas/metadata.py $TARGET
cp ./scripts/gunicorn_start.sh $TARGET
cp ./requirements-api.txt $TARGET

cp ./src/api/__init__.py $TARGET
cp ./src/api/main.py $TARGET
cp ./src/api/openapi.yml $TARGET

mkdir -p $TARGET/.well-known
cp ./src/api/.well-known/ai-plugin.json $TARGET/.well-known
cp ./src/api/.well-known/readme.md $TARGET/.well-known

# make it writable for the group
chmod 775 $TARGET/*.sh
chmod 664 $TARGET/*.py
chmod 664 $TARGET/*.txt

# reload
sudo supervisorctl restart spinorama-api
