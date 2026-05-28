import logging
import argparse
import time
import json
import yaml
import csv
from tqdm import tqdm
import os

from ax.service.ax_client import AxClient, ObjectiveProperties

from utils.base import init_experiment
from utils.bo import BOConfigManager, pbounds_to_ax_parameters
from black_box import black_box_function
from pybamm_runner import build_simulation, solve_simulation
from utils.data import construct_sim_data

time_stamp, RESULTS_DIR = init_experiment(code_dir="BO", SEED=1234)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_dir", type=str, default="./configs")
    return parser.parse_args()

def main():
    logger = logging.getLogger(__name__)

    print("[INFO] Starting Bayesian Optimization pipeline...")
    print(f"[INFO] Time stamp: {time_stamp}")
    print(f"[INFO] Results directory: {RESULTS_DIR}")

    args = parse_args()
    logger.info(f"Args: {args}")

    config_dir = os.path.join(RESULTS_DIR, args.config_dir)
    configs = BOConfigManager(config_dir=config_dir)
    logger.info(f"Configs: {configs.get_all_configs()}")

    start_time = time.time()

    experiment_type = configs.get("exp.EXPERIMENT_TYPE", "real_vs_sim")
    logger.info(f"[INFO] Experiment type: {experiment_type}")

    if experiment_type == "sim_vs_sim":
        run_bo_sim_vs_sim(configs)
    else:
        run_bo_real_vs_sim(configs)

    end_time = time.time()

    print("[INFO] Ending Bayesian Optimization pipeline...")
    print(f"[INFO] Time taken: {end_time - start_time} seconds")
    logger.info(f"[INFO] Time taken: {end_time - start_time} seconds")

def run_bo_real_vs_sim(configs: BOConfigManager):
    logger = logging.getLogger(__name__)

    fixed_parameters = configs.get("BO.fixed_parameters")
    logger.info(f"[INFO] Fixed parameters: {fixed_parameters}")

    scale_factor = configs.get("BO.scale_factor")
    pbounds_range = configs.get_pbounds_range()
    ax_parameters, name_mapping = pbounds_to_ax_parameters(
        pbounds_range, scale_factor=scale_factor)
    logger.info(f"[INFO] AX Parameter bounds: {ax_parameters}")
    logger.info(f"[INFO] AX Name mapping: {name_mapping}")

    try:
        ax_client = AxClient(random_seed = configs.get("exp.RANDOM_SEED"))
        ax_client.create_experiment(
            name="Real Data vs Simulation Bayesian Optimization Experiment",
            parameters=ax_parameters,
            objectives={
                "black_box_output": ObjectiveProperties(minimize=False)
            },
        )

        for exp_idx in tqdm(range(1, configs.get("BO.BO_search_trials") + 1)):
            logger.info(f"[INFO] Trial {exp_idx} started.")

            # INFO:
            # exp_idx used to record the experiment index in the loop
            # trial_index used to record the trial index in ax_client
            parameterization, trial_index = ax_client.get_next_trial()
            parameterization_truth = {
                k: (v / scale_factor)
                for k, v in parameterization.items()
            }
            logger.info(
                f"[INFO] Parameterization Truth [Trial {exp_idx}]: {parameterization_truth}"
            )

            # Local evaluation here can be replaced with deployment to external system.
            objective_value, loss_list, total_loss = black_box_function(
                exp_idx, configs, time_stamp, parameterization, name_mapping,
                scale_factor)
            ax_client.complete_trial(trial_index=trial_index,
                                     raw_data=objective_value)

            logger.info(f"[INFO] Loss list [Trial {exp_idx}]: {loss_list}")
            logger.info(
                f"[INFO] Objective value [Trial {exp_idx}]: {objective_value}")

            with open(f'{RESULTS_DIR}/bo_records.jsonl', 'a') as f:
                f.write(
                    json.dumps({
                        "exp_idx": exp_idx,
                        "parameters": parameterization_truth,
                        "loss_list": loss_list,
                        "total_loss": total_loss,
                        "objective_value": objective_value,
                        "experiment_type": "real_vs_sim"
                    }) + '\n')

            logger.info(f"[INFO] Trial {exp_idx} completed.")

        best_parameters, values = ax_client.get_best_parameters()

        restored_parameters = {
            name_mapping[k]: (v / scale_factor)
            for k, v in best_parameters.items()
        }
        logger.info(f"[INFO] Best parameters: {restored_parameters}")
        print(f"[INFO] Best parameters: {restored_parameters}")
        logger.info(f"[INFO] Best Objective value: {values}")
        print(f"[INFO] Best Objective value: {values}")

        ax_client.save_to_json_file(f"{RESULTS_DIR}/ax_client_saved.json")

        with open(f'{RESULTS_DIR}/best_parameters_real_vs_sim.json', 'w') as f:
            json.dump(
                {
                    "best_parameters": restored_parameters,
                    "best_objective_value": values,
                    "experiment_type": "real_vs_sim",
                    "timestamp": time_stamp
                },
                f,
                indent=4)

        logger.info("[INFO] Optimization results saved.")

    except Exception as e:
        logger.error(f"[ERROR] An error occurred during execution: {e}",
                     exc_info=True)

def run_bo_sim_vs_sim(configs: BOConfigManager):
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

    scale_factor = configs.get("BO.scale_factor")
    pbounds_range = configs.get_pbounds_range()
    ax_parameters, name_mapping = pbounds_to_ax_parameters(
        pbounds_range, scale_factor=scale_factor)
    logger.info(f"[INFO] AX Parameter bounds: {ax_parameters}")
    logger.info(f"[INFO] AX Name mapping: {name_mapping}")

    baseline_sim_data = get_sim_baseline_data(configs=configs)
    if baseline_sim_data is None:
        logger.error(f"[ERROR] Failed to get baseline simulation data")

    try:
        start_time = time.time()

        ax_client = AxClient()
        ax_client.create_experiment(
            name="Simulation vs Simulation Bayesian Optimization Experiment",
            parameters=ax_parameters,
            objectives={
                "black_box_output": ObjectiveProperties(minimize=False)
            },
        )

        best_trial_index = -1
        best_total_loss = 1e10
        best_loss_list = {}
        for exp_idx in tqdm(range(1, configs.get("BO.BO_search_trials") + 1)):
            logger.info(f"[INFO] Trial {exp_idx} started.")

            # INFO:
            # exp_idx used to record the experiment index in the loop
            # trial_index used to record the trial index in ax_client
            parameterization, trial_index = ax_client.get_next_trial()
            parameterization_truth = {
                k: (v / scale_factor)
                for k, v in parameterization.items()
            }
            logger.info(
                f"[INFO] Parameterization Truth [Trial {exp_idx}]: {parameterization_truth}"
            )

            objective_value, loss_list, total_loss = black_box_function(
                exp_idx, configs, time_stamp, parameterization, name_mapping,
                scale_factor, baseline_sim_data)
            ax_client.complete_trial(trial_index=trial_index,
                                     raw_data=objective_value)

            if total_loss < best_total_loss:
                best_trial_index = exp_idx
                best_total_loss = total_loss
                best_loss_list = loss_list

            logger.info(f"[INFO] Loss list [Trial {exp_idx}]: {loss_list}")
            logger.info(
                f"[INFO] Objective value [Trial {exp_idx}]: {objective_value}")

            with open(f'{RESULTS_DIR}/bo_sim_vs_sim_records.jsonl', 'a') as f:
                f.write(
                    json.dumps({
                        "exp_idx": exp_idx,
                        "total_time": time.time() - start_time,
                        "parameters": parameterization_truth,
                        "loss_list": loss_list,
                        "total_loss": total_loss,
                        "objective_value": objective_value,
                        "experiment_type": "sim_vs_sim"
                    }) + '\n')

            logger.info(f"[INFO] Trial {exp_idx} completed.")

        best_parameters, values = ax_client.get_best_parameters()

        restored_parameters = {
            name_mapping[k]: (v / scale_factor)
            for k, v in best_parameters.items()
        }
        logger.info(f"[INFO] Best parameters: {restored_parameters}")
        print(f"[INFO] Best parameters: {restored_parameters}")
        logger.info(f"[INFO] Best Objective value: {values}")
        print(f"[INFO] Best Objective value: {values}")

        ax_client.save_to_json_file(
            f"{RESULTS_DIR}/ax_client_sim_vs_sim_saved.json")

        with open(f'{RESULTS_DIR}/best_parameters_sim_vs_sim.json', 'w') as f:
            json.dump(
                {
                    "timestamp": time_stamp,
                    "experiment_type": "sim_vs_sim",
                    "best_parameters": restored_parameters,
                    "best_objective_value": values,
                    "best_trial_index": best_trial_index,
                    "best_total_loss": best_total_loss,
                    "best_loss_list": best_loss_list
                },
                f,
                indent=4)

        logger.info("[INFO] Optimization results saved.")

    except Exception as e:
        logger.error(f"[ERROR] An error occurred during execution: {e}",
                     exc_info=True)

def get_sim_baseline_data(configs: BOConfigManager):
    logger = logging.getLogger(__name__)
    print(f"[INFO] Getting baseline simulation data...")

    fixed_parameters = configs.get("BO.fixed_parameters", {})

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
            configs, {},
            fixed_parameters)
        logger.info(
            f"[INFO] Baseline simulation changed parameters: {baseline_config.get('parameter_change', {})}"
        )
        logger.info(f"[INFO] Solving baseline simulation...")
        baseline_sim_sol, baseline_solve_time = solve_simulation(baseline_sim)
        baseline_sim_raw_sol, baseline_sim_raw_solve_time = solve_simulation(baseline_sim_raw)
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
        for loss_name in configs.get("BO.loss_setting.loss_type", {}).keys():
            loss_list[loss_name] = {}
            loss_calculator = LossFactory.get_loss(loss_name)
            try:
                kwargs = {
                    'calculate_type':
                    configs.get(
                        f"BO.loss_setting.loss_type.{loss_name}.calculate_type"
                    ),
                    'calculate_cycles':
                    configs.get(
                        f"BO.loss_setting.loss_type.{loss_name}.calculate_cycles"
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
        print(f"[DEBUG] baseline and raw simulation data loss_list: {loss_list}")
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
