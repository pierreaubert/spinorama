#!/bin/bash

cp *sound_power.csv SP.csv
cp *window.csv LW.csv
cp *reflections.csv ER.csv
cp *on_axis.csv On\ Axis.csv

for f in [A-Z]*.csv; do
  awk -F',' 'FNR>1 {print($1 " " $2)}' < "${f}" > "${f%.csv}.txt";
done

rm -f pmc* *.csv *~
