#!/bin/bash

cp spin_*sound_power.csv SP.csv
cp spin_*listening.csv LW.csv
cp spin_*reflections.csv ER.csv
cp spin_*on_axis.csv On\ Axis.csv

for f in [A-Z]*.csv; do
  awk -F',' 'FNR>1 {print($1 " " $2)}' < "${f}" > "${f%.csv}.txt";
done

rm -f spin* *.csv *~
