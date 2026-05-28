EXP_SETTING_INDEX=(4 6 9 15 19 22 28 32 34 37 43 49 51 55 60 62 65 71 75 82 86 91 97 98 103 106 109 111 115 116 117 119 122 125 130 132 133 134 137 142 146 147 150 155 156 159 162 167 170 175 179 184 188 193 196 201 205 210 214 219 224 226 231 233 238 239 241 246 248 253 255 260 261 263 268 270 275 277 280 285 289 293 297 302 309 310 315 318 322 326 331 338 339 344 347 351 355 360 365 372)
for idx in "${EXP_SETTING_INDEX[@]}"; do
    python scripts/update_configs_sim_sim.py --index "$idx" --setting_file ../../generate_simulated_data/output/simulated_data_setting_multi_new_filtered.yaml
    echo "python scripts/update_configs_sim_sim.py --index $idx --setting_file ../../generate_simulated_data/output/simulated_data_setting_multi_new_filtered.yaml"
    python BO/pipeline.py --config_dir configs
done