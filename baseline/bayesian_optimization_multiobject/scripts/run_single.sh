#!/bin/bash

# error=(79 82 94 109 166)
# EXP_SETTING_INDEX=(1 2 6 8 11 13 15 24 25 29 30 34 36 38 47 49 52 54 57 59 70 73 76 82 84 87 89 93 97 98 101 102 108 112 113 115 116 121 122 124 125 126 128 130 132 134 136 138 140 142 144 146 148 150 152 154 156 158 159 160 162 163 164 167 168 169 170 172 174 176 179 180 181 183 185 187 189 192 194 197 198 200 203 204 207 209 212 213 215 218 219 222 224 227 230 233

EXP_SETTING_INDEX=()

for EXP_INDEX in ${EXP_SETTING_INDEX[@]}; do
    echo "Running experiment for EXP_INDEX=[$EXP_INDEX]"
    
    python scripts/update_configs_sim_sim.py --index $EXP_INDEX --setting_file "../../generate_simulated_data/output/simulated_data_setting_single_new_filtered.yaml"
    echo "python scripts/update_configs_sim_sim.py --index $EXP_INDEX --setting_file "
    
    bash scripts/run_sim_vs_sim_experiment.sh
    
done

echo "All experiments completed! 🎉"