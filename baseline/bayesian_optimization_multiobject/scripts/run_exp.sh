#!/bin/bash

INDEX=${1:-1}
SETTING_FILE="../../generate_simulated_data/output/simulated_data_setting_single.yaml"
CONFIG_DIR="configs"
BOUNDS_FACTOR=${2:-0.2}

python scripts/update_configs.py \
    --index "$INDEX" \
    --setting_file "$SETTING_FILE" \
    --config_dir "$CONFIG_DIR" \
    --bounds_factor "$BOUNDS_FACTOR"

python BO/pipeline.py