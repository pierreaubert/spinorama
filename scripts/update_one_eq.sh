#!/bin/bash

OS=$(uname)

if test "$(hostname)" = "horn"; then
    export NUMEXPR_MAX_THREADS=96
fi

# local by default
IP="127.0.0.1"

if test "$OS" = "Linux"; then
    IP=$(ip a | grep 192 | cut -d ' ' -f 6 | cut -d '/' -f 1 | head -1)
elif test "$OS" = "Darwin"; then
    ulimit -n 10240
    IP=$(/sbin/ifconfig| grep 'inet ' | grep broadcast | cut -d ' ' -f 2 | head -1)
fi

PORT=8379

start_ray()
{
    #                                                                        prometheus exporter
    TEMP_DIR=$(pwd)/build/ray
    mkdir -p ./build/ray
    rm -fr /tmp/ray/
    ln -s ${TEMP_DIR} /tmp
    echo "Starting Ray with ${IP} at ${PORT} with tmp set to ${TEMP_DIR}"
    ray start --node-ip-address=${IP} --port ${PORT} --head --dashboard-host=${IP} --metrics-export-port=9101 --disable-usage-stats
}

compute_eq()
{
    EXTRA=""
    smooth="asis"
    if [ "$4" != "" ]; then
	smooth="smooth"
	EXTRA="${EXTRA} $4"
    fi
    full="pk"
    if [ "$5" != "" ]; then
	full="all"
	EXTRA="${EXTRA} $5"
    fi
    target_dir="$(pwd)/build/eqs/$3/$2-$1-$smooth-$full"
    mkdir -p "$target_dir"
    echo  ./generate_peqs.py --verbose --force --optimisation=global --max-iter=15000 --speaker="$3" --max-peq=$1 --fitness=$2 --ray-cluster=$IP:$PORT ${EXTRA}  --output-dir="$target_dir"
    { ./generate_peqs.py \
	  --verbose \
	  --force \
	  --optimisation=global \
	  --max-iter=15000 \
	  --speaker="$3" \
	  --max-peq=$1 \
          --fitness=$2 \
	  --ray-cluster=$IP:$PORT \
	  ${EXTRA} \
	  --output-dir="$target_dir" > "$target_dir.log"; \
    } 2>&1 &
}

start_ray

FAIL=0

for spk in "$@"
do
    compute_eq 3 "Flat" "$spk" "" ""
    compute_eq 4 "Flat" "$spk" "" ""
    compute_eq 5 "Flat" "$spk" "" ""
    compute_eq 6 "Flat" "$spk" "" ""
    compute_eq 7 "Flat" "$spk" "" ""

    compute_eq 3 "Score" "$spk" "" ""
    compute_eq 4 "Score" "$spk" "" ""
    compute_eq 5 "Score" "$spk" "" ""
    compute_eq 6 "Score" "$spk" "" ""
    compute_eq 7 "Score" "$spk" "" ""

    compute_eq 3 "Flat" "$spk" "--smooth-measurements=7 --smooth-order=3" ""
    compute_eq 4 "Flat" "$spk" "--smooth-measurements=7 --smooth-order=3" ""
    compute_eq 5 "Flat" "$spk" "--smooth-measurements=7 --smooth-order=3" ""
    compute_eq 6 "Flat" "$spk" "--smooth-measurements=7 --smooth-order=3" ""
    compute_eq 7 "Flat" "$spk" "--smooth-measurements=7 --smooth-order=3" ""

    compute_eq 3 "Score" "$spk" "--smooth-measurements=7 --smooth-order=3" ""
    compute_eq 4 "Score" "$spk" "--smooth-measurements=7 --smooth-order=3" ""
    compute_eq 5 "Score" "$spk" "--smooth-measurements=7 --smooth-order=3" ""
    compute_eq 6 "Score" "$spk" "--smooth-measurements=7 --smooth-order=3" ""
    compute_eq 7 "Score" "$spk" "--smooth-measurements=7 --smooth-order=3" ""

done

for job in $(jobs -p)
do
    wait $job || let "FAIL+=1"
done

if [ "$FAIL" == "0" ]; then
    echo "YAY!"
else
    echo "FAIL! ($FAIL)"
fi

ray stop
