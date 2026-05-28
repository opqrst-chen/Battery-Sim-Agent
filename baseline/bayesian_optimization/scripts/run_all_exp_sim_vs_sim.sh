# #!/bin/bash

# for EXP_INDEX in {100..890}; do
    
#     python scripts/update_configs_sim_sim.py --index $EXP_INDEX
#     echo "python scripts/update_configs.py --index $EXP_INDEX"
    
#     bash scripts/run_sim_vs_sim_experiment.sh
    
# done

# echo "All experiments completed! 🎉"

# #!/usr/bin/env bash
# set -euo pipefail

# for EXP_INDEX in {1..100}; do
#     echo "Running experiment for EXP_INDEX=[$EXP_INDEX]"

#     python scripts/update_configs_sim_sim.py --index "$EXP_INDEX"

#     timeout --preserve-status -k "$GRACE_PERIOD" "$TIME_LIMIT" \
#             bash scripts/run_sim_vs_sim_experiment.sh

#     # sleep 1
# done

# echo "All experiments completed! 🎉"

#!/usr/bin/env bash
set -euo pipefail
set -m

########################################################
########################################################
TIME_LIMIT="60m"
GRACE_PERIOD="30s"
BATCH_SIZE=5
SLEEP_GAP=5

########################################################
########################################################
cleanup() {
    echo ">>> Caught interrupt, terminating the whole batch ..."

    trap - INT TERM

    kill -TERM -$$ 2>/dev/null || true
    sleep 5

    kill -KILL -$$ 2>/dev/null || true
}
trap cleanup INT TERM

########################################################
########################################################
run_one() {
    local EXP_INDEX="$1"

    echo "Running experiment for EXP_INDEX=[${EXP_INDEX}]"

    python scripts/update_configs_sim_sim.py --index "${EXP_INDEX}"

    timeout --preserve-status -k "${GRACE_PERIOD}" "${TIME_LIMIT}" \
            bash scripts/run_sim_vs_sim_experiment.sh
}

export -f run_one
export TIME_LIMIT GRACE_PERIOD

########################################################
########################################################
for EXP_INDEX in {100..300}; do
    run_one "${EXP_INDEX}" &
    sleep "${SLEEP_GAP}"

    if (( $(jobs -r | wc -l) >= BATCH_SIZE )); then
        wait
    fi
done

wait

echo "All experiments completed! 🎉"
