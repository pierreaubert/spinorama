#!/bin/sh

remove=$1

for i in *hor\ [0-9]*.frd; do j=${i#$1} ; k=${j%.frd} ; cp "$i" "../$SPEAKER _H ${k# hor }.txt"; done
for i in *hor\ -[0-9]*.frd; do j=${i#$1} ; k=${j%.frd} ; cp "$i" "../$SPEAKER _H ${k# hor }.txt"; done
for i in *ver\ [0-9]*.frd; do j=${i#$1} ; k=${j%.frd} ; cp "$i" "../$SPEAKER _V ${k# ver }.txt"; done
for i in *ver\ -[0-9]*.frd; do j=${i#$1} ; k=${j%.frd} ; cp "$i" "../$SPEAKER _V ${k# ver }.txt"; done
