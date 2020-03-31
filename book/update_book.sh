mkdir -p ./tmp
# copy files to tmp
for i in ../docs/[A-Z]*/ASR/default/2cols.jpg; do        
    j=${i#../docs/}      
    speaker1=${j%/ASR/default/2cols.jpg}
    speaker2=${speaker1// /-}
    speaker3=${speaker2//./-}
    cp $i ./tmp/$speaker3.jpg
done
# convert to eps to prevent bounding box complaints
for i in ./tmp/*.jpg; do
    convert $i eps2:${i%.jpg}.eps;
done
#
python3 generate_book.py
#
pdflatex tmp/asrbook.tex
bibtex   tmp/asrbook.tex
pdflatex tmp/asrbook.tex
pdflatex tmp/asrbook.tex
