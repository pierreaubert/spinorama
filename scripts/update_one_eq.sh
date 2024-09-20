#!/bin/bash

if test "$(hostname)" = "horn"; then
    export NUMEXPR_MAX_THREADS=96
fi

IP=192.168.1.36
PORT=9999

start_ray()
{
    #                                                                        prometheus exporter
    ray start --node-ip-address=$IP --port $PORT --head --dashboard-host=$IP --metrics-export-port=9101
}

compute_eq()
{
    target_dir="$(pwd)/build/eqs/$3/$2-$1"
    mkdir -p "$target_dir"
    { ./generate_peqs.py \
	  --verbose \
	  --force \
	  --optimisation=global \
	  --max-iter=15000 \
	  --speaker="$3" \
	  --max-peq=$1 \
          --fitness=$2 \
	  --ray-cluster=$IP:$PORT \
	  --output-dir="$target_dir" > "$target_dir.log"; \
	} 2>&1 &
}

start_ray

FAIL=0

for spk in "$@"
do
    compute_eq 1 "Flat" "$spk"
    compute_eq 2 "Flat" "$spk"
    compute_eq 4 "Flat" "$spk"
    compute_eq 5 "Flat" "$spk"
    compute_eq 6 "Flat" "$spk"
    compute_eq 7 "Flat" "$spk"

    compute_eq 1 "Score" "$spk"
    compute_eq 2 "Score" "$spk"
    compute_eq 4 "Score" "$spk"
    compute_eq 5 "Score" "$spk"
    compute_eq 6 "Score" "$spk"
    compute_eq 7 "Score" "$spk"
done

for job in $(jobs -p)
do
    wait $job || let "FAIL+=1"
done

if [ "$FAIL" == "0" ];
then
    echo "YAY!"
else
    echo "FAIL! ($FAIL)"
fi

ray stop
