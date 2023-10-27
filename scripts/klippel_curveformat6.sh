#!/bin/sh

rm -- *.txt
unzip $1

PATTERN='/^[0-9].*/ {printf("%f,%f\n", $1, $2)}'
SPEAKER=$2

for i in $2_hor_+*.txt; do
    j="${i#$2_hor_+}";
    awk "$PATTERN" "$i" > "${j%.txt}"_H.txt;
done

for i in $2_ver_+*.txt; do
    j="${i#$2_ver_+}";
    awk "$PATTERN" "$i" > "${j%.txt}"_V.txt;
done

for i in $2_hor_-*.txt; do
    j="${i#$2_hor_-}";
    awk "$PATTERN" "$i" > "-${j%.txt}"_H.txt;
done

for i in $2_ver_-*.txt; do
    j="${i#$2_ver_-}";
    awk "$PATTERN" "$i" > "-${j%.txt}"_V.txt;
done
