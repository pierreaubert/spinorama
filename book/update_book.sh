#!/bin/zsh
mkdir -p ./tmp
# copy files to tmp
for i in ../docs/speakers/[A-Z]*/ASR/filters_eq.jpg; do
    j=${i#../docs/speakers}
    speaker1=${j%/ASR/filters_eq.jpg}
    speaker2=${speaker1// /-}
    speaker3=${speaker2//./-}
    cp "$i" ./tmp/$speaker3.jpg
done
# convert to eps to prevent bounding box complaints
for i in ./tmp/*.jpg; do
    convert $i eps2:${i%.jpg}.eps;
done
#
python3 generate_book.py
# latex dance
pdflatex tmp/asrbook.tex
bibtex   tmp/asrbook.tex
pdflatex tmp/asrbook.tex
pdflatex tmp/asrbook.tex
