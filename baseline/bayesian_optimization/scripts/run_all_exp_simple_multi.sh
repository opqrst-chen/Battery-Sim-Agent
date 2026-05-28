#!/bin/bash

# EXP_SETTING_INDEX=(6 9 15 19 22 28 32 34 37 43 49 51 55 60 62 65 71 75 82 86 91 97 98 103 106 109 111 115 116 117 119 122 125 130 132 133 134 137 142 146 147 150 155 156 159 162 167 170 175 179 184 188 193 196 201 205 210 214 219 224 226 231 233 238 239 241 246 248 253 255 260 261 263 268 270 275 277 280 285 289 293 297 302 309 310 315 318 322 326 331 338 339 344 347 351 355 360 365 372)
EXP_SETTING_INDEX=(86 91 97 98 103 106 109 111 115 116 117 119 122 125 130 132 133 134 137 142 146 147 150 155 156 159 162 167 170 175 179 184 188 193 196 201 205 210 214 219)

# for EXP_INDEX in {1..100}; do

for EXP_INDEX in ${EXP_SETTING_INDEX[@]}; do
    echo "Running experiment for EXP_INDEX=[$EXP_INDEX]"
    
    python scripts/update_configs_sim_sim.py --index $EXP_INDEX --setting_file "../../generate_simulated_data/output/simulated_data_setting_multi_new_filtered.yaml"
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
