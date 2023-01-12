for a in 0 10 20 30 40 50 60 70 80 90 100 110 120 130 140 150 160 170 180; do
    tail -n +7 "$1-M0-P$a.txt" > "$1 _H $a.txt";
    tail -n +7 "$1-M90-P$a.txt" > "$1 _V $a.txt";
done

for a in 10 20 30 40 50 60 70 90 80 100 110 120 130 140 150 160 170 180; do
    tail -n +7 "$1-M180-P$a.txt" > "$1 _H -$a.txt";
    tail -n +7 "$1-M270-P$a.txt" > "$1 _V -$a.txt";
done

mv *_H*.txt  *_V*.txt ..
