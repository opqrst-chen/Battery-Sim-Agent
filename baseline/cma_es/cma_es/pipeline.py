import logging
import argparse
import time
import json
import yaml
import csv
from tqdm import tqdm
import os

import cma
from utils.base import init_experiment
from utils.cma_es import CMAESConfigManager
from black_box import black_box_function
from pybamm_runner import build_simulation, solve_simulation
from utils.data import construct_sim_data

time_stamp, RESULTS_DIR = init_experiment(code_dir="cma_es", SEED=1234)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_dir", type=str, default="./configs")
    return parser.parse_args()

def main():
    logger = logging.getLogger(__name__)

    print(
        "[INFO] Starting Covariance Matrix Adaptation Evolution Strategy pipeline..."
    )
    print(f"[INFO] Time stamp: {time_stamp}")
    print(f"[INFO] Results directory: {RESULTS_DIR}")

    args = parse_args()
    logger.info(f"Args: {args}")

    config_dir = os.path.join(RESULTS_DIR, args.config_dir)
    configs = CMAESConfigManager(config_dir=config_dir)
    logger.info(f"Configs: {configs.get_all_configs()}")

    start_time = time.time()

    experiment_type = configs.get("exp.EXPERIMENT_TYPE", "sim_vs_sim")
    logger.info(f"[INFO] Experiment type: {experiment_type}")

    if experiment_type == "sim_vs_sim":
        run_cma_es_sim_vs_sim(configs)
    else:
        pass

    end_time = time.time()

    print(
        "[INFO] Ending Covariance Matrix Adaptation Evolution Strategy pipeline..."
    )
    print(f"[INFO] Time taken: {end_time - start_time} seconds")
    logger.info(f"[INFO] Time taken: {end_time - start_time} seconds")

def run_cma_es_sim_vs_sim(configs: CMAESConfigManager):
    logger = logging.getLogger(__name__)

    exp_setting_path = os.path.join(os.path.dirname(RESULTS_DIR),
                                    'exp_setting.csv')
    file_exists = os.path.isfile(exp_setting_path)
    with open(exp_setting_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            print(f"[INFO] Writing exp setting to {exp_setting_path}")
            writer.writerow(['exp_index', 'time_stamp'])
        writer.writerow(
            [configs.get("exp.SIM_VS_SIM.baseline_sim_id"), time_stamp])

    experiment_type = configs.get("exp.EXPERIMENT_TYPE")
    if experiment_type != "sim_vs_sim":
        logger.warning(
            f"[WARNING] Expected experiment_type 'sim_vs_sim', got '{experiment_type}'"
        )

    baseline_sim_data = get_sim_baseline_data(configs=configs)
    if baseline_sim_data is None:
        logger.error(f"[ERROR] Failed to get baseline simulation data")
        return

    try:
        start_time = time.time()

        x0, params_name, x0_lower_bounds, x0_upper_bounds = configs.get_x_0()

        generations = configs.get("cma_es.search_trials")
        popsize = configs.get("cma_es.popsize", None)

        es = cma.CMAEvolutionStrategy(x0=x0,
                                      sigma0=configs.get("cma_es.sigma0"),
                                      inopts={
                                          "bounds": [x0_lower_bounds, x0_upper_bounds],
                                          'maxiter': generations,
                                          'popsize': popsize,
                                          'seed':
                                          configs.get("exp.RANDOM_SEED"),
                                          'verb_disp': 1,
                                          'tolfun': 0,
                                          'tolx': 0,
                                          'tolfunhist': 0,
                                          'tolstagnation': 0,
                                          'tolflatfitness': 0
                                      })

        logger.info(
            f"[INFO] CMA-ES configured generations (maxiter): {es.opts['maxiter']}"
        )
        logger.info(f"[INFO] CMA-ES configured popsize: {es.popsize}")
        logger.info(
            f"[INFO] Expected total black-box calls: {es.opts['maxiter'] * es.popsize}"
        )

        best_trial_index = None
        best_total_loss = float('inf')
        best_loss_list = {}
        best_params = None
        history_params = []
        history_loss = []

        for generation_idx in range(1, generations + 1):
            logger.info(
                f"[INFO] ===== Generation {generation_idx} started =====")

            solutions = es.ask()
            fitness = []

            for subtrial_idx, params in enumerate(solutions, start=1):
                logger.info(
                    f"[INFO] Generation {generation_idx} - Subtrial {subtrial_idx} started."
                )

                parameterization_truth = {
                    params_name[i]: params[i]
                    for i in range(len(params_name))
                }

                logger.info(
                    f"[INFO] Parameterization Truth: {parameterization_truth}")

                objective_value, loss_list, total_loss = black_box_function(
                    f"gen_{generation_idx}_subtrial_{subtrial_idx}", configs,
                    time_stamp, parameterization_truth, baseline_sim_data)

                fitness.append(total_loss)

                if total_loss < best_total_loss:
                    best_trial_index = f"gen_{generation_idx}_subtrial_{subtrial_idx}"
                    best_total_loss = total_loss
                    best_loss_list = loss_list
                    best_params = parameterization_truth

                logger.info(f"[INFO] Loss list: {loss_list}")
                logger.info(f"[INFO] Objective value: {objective_value}")

                with open(f'{RESULTS_DIR}/cma_es_sim_vs_sim_records.jsonl',
                          'a') as f:
                    f.write(
                        json.dumps({
                            "exp_idx":
                            f"gen_{generation_idx}_subtrial_{subtrial_idx}",
                            "total_time": time.time() - start_time,
                            "parameters": parameterization_truth,
                            "loss_list": loss_list,
                            "total_loss": total_loss,
                            "objective_value": objective_value,
                            "experiment_type": "sim_vs_sim"
                        }) + '\n')

                logger.info(
                    f"[INFO] Generation {generation_idx} - Subtrial {subtrial_idx} completed."
                )

            es.tell(solutions, fitness)
            es.disp()

            history_params.append(es.result.xbest.tolist())
            history_loss.append(es.result.fbest)

            logger.info(
                f"[INFO] ===== Generation {generation_idx} completed =====")

        logger.info(
            f"[INFO] Forced run completed. Total generations: {generations}")

        logger.info(f"[INFO] Best parameters: {best_params}")
        print(f"[INFO] Best parameters: {best_params}")
        logger.info(f"[INFO] Best total loss: {best_total_loss}")
        print(f"[INFO] Best total loss: {best_total_loss}")

        with open(f'{RESULTS_DIR}/best_parameters_sim_vs_sim.json', 'w') as f:
            json.dump(
                {
                    "timestamp": time_stamp,
                    "experiment_type": "sim_vs_sim",
                    "best_parameters": best_params,
                    "best_total_loss": best_total_loss,
                    "best_trial_index": best_trial_index,
                    "best_loss_list": best_loss_list
                },
                f,
                indent=4)

        import pandas as pd
        df = pd.DataFrame({
            'generation': range(1,
                                len(history_loss) + 1),
            'best_params': history_params,
            'best_loss': history_loss
        })
        df.to_csv(f"{RESULTS_DIR}/cmaes_optimization_history.csv", index=False)
        logger.info("[INFO] Optimization history saved.")
        print("[INFO] Optimization history saved.")

    except Exception as e:
        logger.error(f"[ERROR] An error occurred during execution: {e}",
                     exc_info=True)

def get_sim_baseline_data(configs: CMAESConfigManager):
    logger = logging.getLogger(__name__)
    print(f"[INFO] Getting baseline simulation data...")

    fixed_parameters = configs.get("cma_es.fixed_parameters", {})

    baseline_sim_config_path = configs.get(
        "exp.SIM_VS_SIM.baseline_sim_config")
    baseline_sim_id = configs.get("exp.SIM_VS_SIM.baseline_sim_id", 1)

    if not os.path.exists(baseline_sim_config_path):
        logger.error(
            f"[ERROR] Baseline simulation config not found: {baseline_sim_config_path}"
        )
        return None

    with open(baseline_sim_config_path, 'r', encoding='utf-8') as f:
        baseline_configs = yaml.safe_load(f)

    if baseline_sim_id not in baseline_configs:
        logger.error(
            f"[ERROR] Baseline simulation ID {baseline_sim_id} not found in config"
        )
        return None

    baseline_config = baseline_configs[baseline_sim_id]
    logger.info(f"[INFO] Baseline config: {baseline_config}")

    baseline_sim_data = {}
    try:
        logger.info(f"[INFO] Building baseline simulation...")
        baseline_sim, baseline_param = build_simulation(
            configs, baseline_config.get("parameter_change", {}),
            fixed_parameters)
        baseline_sim_raw, baseline_param_raw = build_simulation(
            configs, {}, fixed_parameters)
        logger.info(
            f"[INFO] Baseline simulation changed parameters: {baseline_config.get('parameter_change', {})}"
        )
        logger.info(f"[INFO] Solving baseline simulation...")
        baseline_sim_sol, baseline_solve_time = solve_simulation(baseline_sim)
        baseline_sim_raw_sol, baseline_sim_raw_solve_time = solve_simulation(
            baseline_sim_raw)
        logger.info(f"[INFO] Constructing baseline simulation data...")
        logger.info(f"[INFO] Baseline simulation data")
        baseline_sim_data = construct_sim_data(baseline_sim_sol)
        logger.info(f"[INFO] Baseline simulation raw data")
        baseline_sim_raw_data = construct_sim_data(baseline_sim_raw_sol)
        logger.info(f"[INFO] Baseline simulation data constructed.")
        print(f"[INFO] Baseline simulation data constructed.")

        logger.info(f"[INFO] Baseline simulation data loss calculation.")
        from loss.factory import LossFactory
        loss_list = {}
        for loss_name in configs.get("cma_es.loss_setting.loss_type",
                                     {}).keys():
            loss_list[loss_name] = {}
            loss_calculator = LossFactory.get_loss(loss_name)
            try:
                kwargs = {
                    'calculate_type':
                    configs.get(
                        f"cma_es.loss_setting.loss_type.{loss_name}.calculate_type"
                    ),
                    'calculate_cycles':
                    configs.get(
                        f"cma_es.loss_setting.loss_type.{loss_name}.calculate_cycles"
                    ),
                    'experiment_type':
                    "sim_vs_sim"
                }

                loss_value = loss_calculator.calculate_loss(
                    baseline_sim_data, baseline_sim_raw_data, **kwargs)
                loss_list[loss_name]["loss_value"] = loss_value
                logger.info(f"[INFO] Loss of {loss_name}: {loss_value}")

            except Exception as e:
                logger.error(f"[ERROR] Error in {loss_name} calculation: {e}")
                loss_list[loss_name]["loss_value"] = -1e6

        print("#" * 88)
        print(
            f"[DEBUG] baseline and raw simulation data loss_list: {loss_list}")
        print("#" * 88)

        total_loss = LossFactory.get_loss("total").calculate_loss(
            loss_list=loss_list)
        print(f"[DEBUG] total_loss: {total_loss}")
        print(f"[INFO] Baseline simulation data loss calculation.")

        return baseline_sim_data
    except Exception as e:
        logger.error(f"[ERROR] Error in baseline PyBaMM simulation: {e}")
        print(f"[ERROR] Error in baseline PyBaMM simulation: {e}")
        return None

if __name__ == "__main__":
    main()
