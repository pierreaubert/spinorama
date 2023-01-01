for i in ../ASR/*; do d=$(basename $i); if ! test -d $d; then mkdir "$d"; fi; done
