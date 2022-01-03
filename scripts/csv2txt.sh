CSV=$1

awk 'BEGIN {FS=";" }{gsub(/"/, ""); gsub(/,/, "."); print($1" "$2" 0");}' "$1" > "On Axis.txt"
awk 'BEGIN {FS=";" }{gsub(/"/, ""); gsub(/,/, "."); print($1" "$3" 0");}' "$1" > "LW.txt"
awk 'BEGIN {FS=";" }{gsub(/"/, ""); gsub(/,/, "."); print($1" "$4" 0");}' "$1" > "SP.txt"
awk 'BEGIN {FS=";" }{gsub(/"/, ""); gsub(/,/, "."); print($1" "$16" 0");}' "$1" > "ER.txt"
awk 'BEGIN {FS=";" }{gsub(/"/, ""); gsub(/,/, "."); print($1" "$5" 0");}' "$1" > "DI.txt"
