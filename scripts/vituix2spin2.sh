#!/bin/sh

cp hor0.txt "../$SPEAKER _H 0.txt"
cp ver0.txt "../$SPEAKER _V 0.txt"
for i in *hor\+*.txt; do cp "$i" "../$SPEAKER _H ${i#hor+}"; done
for i in *ver\+*.txt; do cp "$i" "../$SPEAKER _V ${i#ver+}"; done
for i in *hor\-*.txt; do cp "$i" "../$SPEAKER _H -${i#hor-}"; done
for i in *ver\-*.txt; do cp "$i" "../$SPEAKER _V -${i#ver-}"; done
