#!/bin/bash

NAME=spinorama-api
DIR=/var/www/html/spinorama-api
USER=spinorama-api-user
GROUP=spinorama-api-user
WORKERS=10
WORKER_CLASS=uvicorn.workers.UvicornWorker
VENV=$DIR/.venv/bin/activate
BIND=unix:$DIR/run/gunicorn.sock
LOG_LEVEL=info

cd $DIR
source $VENV

export PYTHONPATH=/var/www/html/spinorama-api

exec gunicorn main:app \
  --name $NAME \
  --workers $WORKERS \
  --worker-class $WORKER_CLASS \
  --user=$USER \
  --group=$GROUP \
  --bind=$BIND \
  --log-level=$LOG_LEVEL \
  --log-file=$DIR/logs/access.log
