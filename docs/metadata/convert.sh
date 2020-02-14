for i in originals/*.jpg; do convert "$i" -define jpeg:size=300x500  -thumbnail '200x300>' -gravity center -extent 200x300 "${i#originals/}"; done
