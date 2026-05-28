#!/bin/bash

echo "Starting Bayesian Optimization Experiment..."

cd "$(dirname "$0")/.."
echo "$(dirname "$0")/.."
# mkdir -p runs

python BO/pipeline.py --config_dir configs

echo "Bayesian Optimization experiment completed!"
echo "Check the results directory for output files."
echo ""
echo "Note: The experiment type is automatically determined from the configuration file."
echo "To change the experiment type, modify the 'experiment_type' field in configs/BO.yaml:"
echo "  - 'real_vs_sim': Real data vs Simulation (default)"
echo "  - 'sim_vs_sim': Simulation vs Simulation"
