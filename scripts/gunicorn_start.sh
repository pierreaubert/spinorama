#!/bin/bash

NAME=spinorama-api
DIR=/home/spin/run/spin-api
USER=spin
GROUP=spin
WORKERS=10
WORKER_CLASS=uvicorn.workers.UvicornWorker
VENV=$DIR/.venv/bin/activate
BIND=unix:/home/spin/run/gunicorn.sock
LOG_LEVEL=info

cd $DIR
source $VENV

export PYTHONPATH=$DIR

exec gunicorn main:app \
  --name $NAME \
  --workers $WORKERS \
  --worker-class $WORKER_CLASS \
  --user=$USER \
  --group=$GROUP \
  --bind=$BIND \
  --log-level=$LOG_LEVEL \
  --log-file=/home/spin/log/api.log
