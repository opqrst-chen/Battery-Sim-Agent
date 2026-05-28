#!/bin/bash

echo "Starting Covariance Matrix Adaptation Evolution Strategy Experiment..."

cd "$(dirname "$0")/.."

mkdir -p results

python cma_es/pipeline.py --config_dir configs

echo "CMA_ES experiment completed!"
echo "Check the results directory for output files."
echo ""
echo "Note: The experiment type is automatically determined from the configuration file."
echo "To change the experiment type, modify the 'experiment_type' field in configs/cma_es.yaml:"
echo "  - 'real_vs_sim': Real data vs Simulation (default)"
echo "  - 'sim_vs_sim': Simulation vs Simulation"
