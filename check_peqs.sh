awk -F',' '{n++; o=o+$2; s=s+$4-$2; if ($4<$2) print "ERROR "$1" " $2" "$4} END {print "Sum Score "o" Sum improvement "s; print "Average score " o/n, "Average delta "s/n}' results_scores.csv
