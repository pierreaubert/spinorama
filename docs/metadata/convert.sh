for i in originals/*.jpg; do 
    convert "$i" -resize 200x500  "${i#originals/}";
done
