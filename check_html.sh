#!/bin/sh

status=0
for d in docs/*.html; do
    msg=$(./node_modules/.bin/html-validator --file="$d");
    if test "$msg" != "Page is valid"; then
        status = 1;
        echo "Linting $d (ERROR)";
	./node_modules/.bin/html-validator --file="$d" --verbose;
    fi
done

if test $status -eq 0; then
    echo "all files are clean!";
    exit 0;
else
    exit 1;
fi
