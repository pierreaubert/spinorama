#!/bin/sh
cat *.header | awk -F',' 'BEGIN {} {for( i=1 ; i<NF; i+=1) { print i, $i;} }'

cat Mesanovic\ RTM10.data |  awk -F',' '{print($1, $2, '0.0');}' > On\ Axis.txt
cat Mesanovic\ RTM10.data |  awk -F',' '{print($1, $3, '0.0');}' > LW.txt
cat Mesanovic\ RTM10.data |  awk -F',' '{print($1, $4, '0.0');}' > SP.txt
cat Mesanovic\ RTM10.data |  awk -F',' '{print($1, $5, '0.0');}' > DI.txt
cat Mesanovic\ RTM10.data |  awk -F',' '{print($1, $16, '0.0');}' > ER.txt
cat Mesanovic\ RTM10.data |  awk -F',' '{print($1, $15, '0.0');}' > ERDI.txt
