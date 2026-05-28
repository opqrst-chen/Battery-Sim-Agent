#!/bin/bash

# error=()
# COMPLETE_EXP_SETTING_INDEX=()
EXP_SETTING_INDEX=(1 2 6 8 11 13 15 24 25 29 30 34 36 38 47 49 52 54 57 59 70 73 76 79 82 84 87 89 93 94 97 98 101 102 108 109 112 113 115 116 121 122 124 125 126 128 130 132 134 136 138 140 142 144 146 148 150 152 154 156 158 159 160 162 163 164 166 167 168 169 170 172 174 176 179 180 181 183 185 187 189 192 194 197 198 200 203 204 207 209 212 213 215 218 219 222 224 227 230 233)

# for EXP_INDEX in {1..100}; do

for EXP_INDEX in ${EXP_SETTING_INDEX[@]}; do
    echo "Running experiment for EXP_INDEX=[$EXP_INDEX]"
    
    python scripts/update_configs_sim_sim.py --index $EXP_INDEX --setting_file "../../generate_simulated_data/output/simulated_data_setting_single_new_filtered.yaml"
    echo "python scripts/update_configs_sim_sim.py --index $EXP_INDEX --setting_file "
    
    bash scripts/run_sim_vs_sim_experiment.sh
    
done

echo "All experiments completed! 🎉"

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

# #!/usr/bin/env bash
# set -euo pipefail

# ########################################################
# ########################################################

# ########################################################
# ########################################################
# cleanup() {
#     echo ">>> Caught interrupt, terminating the whole batch ..."

#     trap - INT TERM

#     kill -TERM -$$ 2>/dev/null || true

#     kill -KILL -$$ 2>/dev/null || true
# }

# ########################################################
# ########################################################
# run_one() {
#     local EXP_INDEX="$1"

#     echo "Running experiment for EXP_INDEX=[${EXP_INDEX}]"

#     python scripts/update_configs_sim_sim.py --index "${EXP_INDEX}"

#     timeout --preserve-status -k "${GRACE_PERIOD}" "${TIME_LIMIT}" \
#             bash scripts/run_sim_vs_sim_experiment.sh
# }

# export -f run_one

# ########################################################
# ########################################################
# for EXP_INDEX in {1..100}; do
#     sleep "${SLEEP_GAP}"

#     if (( $(jobs -r | wc -l) >= BATCH_SIZE )); then
#     fi
# done

# echo "All experiments completed! 🎉"
