#!/bin/bash

# #!/usr/bin/env bash
# set -euo pipefail

# # EXP_SETTING_INDEX=(1 2 6 8 11 13)
EXP_SETTING_INDEX=(1 2 6 8 11 13 15 24 25 29 30 34 36 38 47 49 52 54 57 59 70 73 76 79 82 84 87 89 93 94 97 98 101 102 108 109 112 113 115 116 121 122 124 125 126 128 130 132 134 136 138 140 142 144 146 148 150 152 154 156 158 159 160 162 163 164 166 167 168 169 170 172 174 176 179 180 181 183 185 187 189 192 194 197 198 200 203 204 207 209 212 213 215 218 219 222 224 227 230 233)
MAX_JOBS=5   # <- run up to 3 experiments in parallel; tune for your machine

run_one() {
  local idx="$1"
  echo "[${idx}] starting"
  python scripts/update_configs_sim_sim.py --index "$idx"
  echo "python scripts/update_configs_sim_sim.py --index $idx"
  # capture logs per run
  bash scripts/run_sim_vs_sim_experiment.sh >"./baseline/bayesian_optimization/logs/run_${idx}.out" 2>"./baseline/bayesian_optimization/logs/run_${idx}.err"
  echo "[${idx}] done"
}

mkdir -p ./baseline/bayesian_optimization/logs

# graceful Ctrl-C: kill all children
trap 'echo "Stopping…"; jobs -p | xargs -r kill 2>/dev/null || true; wait' INT TERM

for EXP_INDEX in "${EXP_SETTING_INDEX[@]}"; do
  run_one "$EXP_INDEX" &
  # if we already have MAX_JOBS running, wait for one to finish
  while (( $(jobs -p | wc -l) >= MAX_JOBS )); do
    wait -n
  done
done

# wait for the remaining jobs
wait
echo "All experiments completed! 🎉"

# # EXP_SETTING_INDEX=(1 2 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 28 29 30 32 33 34 35 36 37 38 39 40 41 42 43 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 68 69 70 72 73 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 233)
# EXP_SETTING_INDEX=(1 2 6 8 11 13)
# # EXP_SETTING_INDEX=(1)

# for EXP_INDEX in {1..100}; do

# for EXP_INDEX in ${EXP_SETTING_INDEX[@]}; do
    
#     python scripts/update_configs_sim_sim.py --index $EXP_INDEX
#     echo "python scripts/update_configs_sim_sim.py --index $EXP_INDEX"
    
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
