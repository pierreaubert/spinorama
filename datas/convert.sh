# convert is from imagemagick package
targetdir=../docs/metadata
for i in originals/*.jpg; do 
   smaller="${i#originals/}"
   if ! test -f "$targetdir/$smaller"; then
       echo convert "$i" -define jpeg:size=300x500  -thumbnail '200x300>' -gravity center -extent 200x300 "$smaller";
       convert "$i" -define jpeg:size=300x500  -thumbnail '200x300>' -gravity center -extent 200x300 "$targetdir/$smaller";
   fi
done
