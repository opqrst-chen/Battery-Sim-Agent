# #!/bin/bash

# SETTING_FILE="../../generate_simulated_data/output/simulated_data_setting_single.yaml"
# CONFIG_DIR="configs"

# for INDEX in $(seq 1 890); do

#     python scripts/update_configs.py \
#         --index "$INDEX" \
#         --setting_file "$SETTING_FILE" \
#         --config_dir "$CONFIG_DIR" \
#         --bounds_factor "$BOUNDS_FACTOR"

#     python BO/pipeline.py

# done

#!/bin/bash

SETTING_FILE="../../generate_simulated_data/output/simulated_data_setting_single.yaml"
CONFIG_DIR="configs"
BOUNDS_FACTOR=${1:-0.2}
BATCH_SIZE=${2:-15}

INDEX_LIST=($(python check_bo_records.py --missing-only))

LOG_FILE="timeout_kill.log"
> "$LOG_FILE"

cleanup_old_processes() {
    echo ">>> Checking for python BO/pipeline.py processes running >30 min..."
    ps -eo pid,etimes,cmd --no-headers \
        | grep -E "python(3)? .*BO/pipeline.py" \
        | grep -v grep \
        | awk '$2 > 1800 {print $1, $2, substr($0, index($0,$3))}' \
        | while read pid etimes cmd; do
            echo "    killing PID=$pid (running ${etimes}s) CMD=$cmd"
            kill -9 "$pid"
            echo "[`date '+%Y-%m-%d %H:%M:%S'`] killed stale PID=$pid (running ${etimes}s) CMD=$cmd" >> "$LOG_FILE"
        done
}

total=${#INDEX_LIST[@]}
for ((i=0; i<total; i+=BATCH_SIZE)); do
    batch_end=$((i+BATCH_SIZE))
    if (( batch_end > total )); then
        batch_end=$total
    fi

    echo "===== starting batch: ${INDEX_LIST[i]} ~ ${INDEX_LIST[batch_end-1]} ====="
    cleanup_old_processes

    for ((j=i; j<batch_end; j++)); do
        idx=${INDEX_LIST[j]}
        echo "  starting INDEX=$idx"

        (
            python scripts/update_configs.py \
                --index "$idx" \
                --setting_file "$SETTING_FILE" \
                --config_dir "$CONFIG_DIR" \
                --bounds_factor "$BOUNDS_FACTOR"

            if ! timeout --kill-after=10s 1800 python BO/pipeline.py; then
                echo "[`date '+%Y-%m-%d %H:%M:%S'`] INDEX=$idx timed out (>30min), terminated" | tee -a "$LOG_FILE"
            fi
        ) &

        sleep 2
    done

    wait
    echo "===== batch ${INDEX_LIST[i]} ~ ${INDEX_LIST[batch_end-1]} done ====="
done
