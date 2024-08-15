for i in raw/[A-Z]*.txt; do
    sort -n raw/low.txt | sed -e 's/,//g' > ${i#raw/};
    sort -n ${i} | sed -e 's/,//g' >> ${i#raw/};
done

mv ON.txt On\ Axis.txt
