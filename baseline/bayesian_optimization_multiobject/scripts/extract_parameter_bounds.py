#!/usr/bin/env python3

import yaml
import os
from collections import defaultdict

def extract_parameter_bounds(yaml_file_path):
    if not os.path.exists(yaml_file_path):
        raise FileNotFoundError(f"YAML file not found: {yaml_file_path}")

    with open(yaml_file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    parameter_values = defaultdict(list)

    for config_id, config in data.items():
        if 'parameter_change' in config:
            for param_name, param_value in config['parameter_change'].items():
                parameter_values[param_name].append(param_value)

    parameter_bounds = {}
    for param_name, values in parameter_values.items():
        if values:
            min_val = min(values)
            max_val = max(values)
            parameter_bounds[param_name] = {
                'min': min_val,
                'max': max_val,
                'count': len(values)
            }

    return parameter_bounds

def generate_bo_config(parameter_bounds,
                       output_file="BO_sim_vs_sim_generated.yaml"):
    config = {
        'BO_search_trials': 20,
        'battery': {
            'nominal_capacity': 1.1,
            'experiment_type': 'sim_vs_sim',
            'baseline_sim_config':
            'generate_simulated_data/output/simulated_data_setting_single.yaml',
            'baseline_sim_id': 1
        },
        'loss_setting': {
            'loss_type': {
                'capacity': {
                    'calculate_cycles': [1],
                    'calculate_type': ['rmse', 'mape']
                },
                'current': {
                    'calculate_cycles': [1],
                    'calculate_type': ['rmse', 'mape']
                },
                'voltage': {
                    'calculate_cycles': [1],
                    'calculate_type': ['rmse', 'mape']
                }
            }
        },
        'pbounds': {},
        'scale_factor': 10000000000.0
    }

    for param_name, bounds in parameter_bounds.items():
        config['pbounds'][param_name] = {
            'min': bounds['min'],
            'max': bounds['max']
        }

    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(config,
                  f,
                  default_flow_style=False,
                  allow_unicode=True,
                  indent=2)

    print(f"Generated BO config file: {output_file}")
    return config

def main():
    yaml_file = "../../generate_simulated_data/output/simulated_data_setting_single.yaml"

    try:
        print(f"Extracting parameter bounds from {yaml_file}...")
        parameter_bounds = extract_parameter_bounds(yaml_file)

        print("\nExtracted parameter bounds:")
        print("=" * 80)
        for param_name, bounds in parameter_bounds.items():
            print(f"{param_name}:")
            print(f"  Min: {bounds['min']}")
            print(f"  Max: {bounds['max']}")
            print(f"  Count: {bounds['count']}")
            print()

        print("Generating BO configuration file...")
        config = generate_bo_config(parameter_bounds)

        print(f"\nTotal parameters found: {len(parameter_bounds)}")
        print("Configuration generation completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
