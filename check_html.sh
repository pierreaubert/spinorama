#!/bin/zsh

for d in docs/*.html; do
    echo "Linting $d";
    ./node_modules/.bin/html-validator --file="$d";
done
