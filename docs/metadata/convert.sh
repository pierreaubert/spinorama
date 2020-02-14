for i in originals/*.jpg; do 
    convert "$i" -resize 500x500  "${i#originals/}"; 
done
