#!/bin/sh

status=0
for d in docs/*.html; do
    sz=$(stat -c %s "$d")
    if test $sz -eq 0; then
        status=1;
        echo "$d is empty (ERROR)";
    else
        msg=$(./node_modules/.bin/html-validator --format=html --file="$d");
        if test -n "$msg"; then
            status=1;
            echo "Linting $d (ERROR)";
    	    ./node_modules/.bin/html-validator --format=html --file="$d" --verbose;
        fi
    fi
done

if test $status -eq 0; then
    echo "all files are clean!";
    exit 0;
else
    exit 1;
fi
