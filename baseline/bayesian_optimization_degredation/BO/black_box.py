import time
import json
import logging
import yaml
import os

from loss.factory import LossFactory
from utils.data import load_and_visualize_real_data, construct_sim_data
from pybamm_runner import build_simulation, solve_simulation

logger = logging.getLogger(__name__)

def black_box_function(exp_idx,
                       configs,
                       time_stamp,
                       parameterization,
                       name_mapping,
                       scale_factor,
                       baseline_sim_data=None):
    experiment_type = configs.get("exp.EXPERIMENT_TYPE", "real_vs_sim")

    if experiment_type == "sim_vs_sim":
        return black_box_function_sim_vs_sim(exp_idx, configs, time_stamp,
                                             parameterization, name_mapping,
                                             scale_factor, baseline_sim_data)
    else:
        return black_box_function_real_vs_sim(exp_idx, configs, time_stamp,
                                              parameterization, name_mapping,
                                              scale_factor)

def black_box_function_real_vs_sim(exp_idx, configs, time_stamp,
                                   parameterization, name_mapping,
                                   scale_factor):
    iteration_start_time = time.time()
    total_loss = -1e6

    fixed_parameters = configs.get("BO.fixed_parameters", {})

    parameterization_backup = parameterization.copy()
    parameterization = {
        name_mapping[k]: (v / scale_factor)
        for k, v in parameterization.items()
    }
    for param, value in parameterization.items():
        if value == 0:
            logger.info(f"[WARNING] parameter {param} is zero!")

    loss_list = {}
    for loss_name in configs.get("BO.loss_setting.loss_type").keys():
        loss_list[loss_name] = {}
        loss_list[loss_name]["loss_name"] = loss_name
        loss_list[loss_name]["loss_value"] = total_loss

    try:
        real_data = load_and_visualize_real_data(time_stamp=time_stamp)
        sim_data = {}

        # run pybamm simulation
        try:
            logger.info(f"[INFO] Building simulation...")
            sim, param = build_simulation(configs, parameterization,
                                          fixed_parameters)
            logger.info(f"[INFO] Solving simulation...")
            sim_sol, solve_time = solve_simulation(sim)
            logger.info(f"[INFO] Constructing simulation data...")
            sim_data = construct_sim_data(sim_sol)
            logger.info(f"[INFO] Construct simulation data done.")

            # TODO: plot curves
            from utils.plot import plot_multiple_curves
            context, detail_info = plot_multiple_curves(
                sim=sim,
                ori_data=real_data['cycle_data'],
                cycle_idxs=[1],
                is_plot=False,
                is_save=True,
                save_dir=f'./results/{time_stamp}/plot',
                model='SPMe',
                param='Ai2020',
                id=f'sim_exp_{exp_idx}')
        except Exception as e:
            logger.info(f"[Error] in PyBaMM simulation: {e}")
            return total_loss

        # LOSS ALL
        for loss_name, value in loss_list.items():
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
                    "real_vs_sim"
                }
                loss_value = loss_calculator.calculate_loss(
                    real_data, sim_data, **kwargs)
                loss_list[loss_name]["loss_value"] = loss_value
                logger.info(f"[INFO] Loss of {loss_name}: {loss_value}")

            except Exception as e:
                logger.info(f"[ERROR] Error in {loss_name} calculation: {e}")
                loss_list[loss_name]["loss_value"] = -1e6

        print("#" * 88)
        print(f"[DEBUG] loss_list: {loss_list}")
        print("#" * 88)
        total_loss = LossFactory.get_loss("total").calculate_loss(
            loss_list=loss_list)
        print(f"[DEBUG] total_loss: {total_loss}")

    except Exception as e:
        logger.info(f"[ERROR] Error in black_box_function: {e}")

    finally:
        iteration_end_time = time.time()
        elapsed_time = iteration_end_time - iteration_start_time
        logger.info(f"[INFO] Total loss calculated: {total_loss}")
        logger.info(f"[INFO] loss_list: {loss_list}")
        logger.info(
            f"[INFO] Iteration completed. Time of this iteration: {elapsed_time:.2f} seconds."
        )
        return {
            "black_box_output": (-abs(total_loss), 0.0)
        }, loss_list, total_loss

def black_box_function_sim_vs_sim(exp_idx, configs, time_stamp,
                                  parameterization, name_mapping, scale_factor,
                                  baseline_sim_data):
    iteration_start_time = time.time()
    total_loss = -1e6

    fixed_parameters = configs.get("BO.fixed_parameters", {})

    parameterization_backup = parameterization.copy()
    parameterization = {
        name_mapping[k]: (v / scale_factor)
        for k, v in parameterization.items()
    }

    for param, value in parameterization.items():
        if value == 0:
            logger.info(f"[WARNING] parameter {param} is zero!")

    loss_list = {}
    for loss_name in configs.get("BO.loss_setting.loss_type").keys():
        loss_list[loss_name] = {}
        loss_list[loss_name]["loss_name"] = loss_name
        loss_list[loss_name]["loss_value"] = total_loss

    try:
        if baseline_sim_data is None:
            logger.error(f"[ERROR] Baseline simulation data is None")
            return total_loss

        current_sim_data = {}
        try:
            logger.info(f"[INFO] Building current simulation...")
            current_sim, current_param = build_simulation(
                configs, parameterization, fixed_parameters)
            logger.info(f"[INFO] Solving current simulation...")
            current_sim_sol, current_solve_time = solve_simulation(current_sim)
            logger.info(f"[INFO] Constructing current simulation data...")
            current_sim_data = construct_sim_data(current_sim_sol)
            logger.info(f"[INFO] Current simulation data constructed.")
        except Exception as e:
            logger.error(f"[ERROR] Error in current PyBaMM simulation: {e}")
            return total_loss

        for loss_name, value in loss_list.items():
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
                    baseline_sim_data, current_sim_data, **kwargs)
                loss_list[loss_name]["loss_value"] = loss_value
                logger.info(f"[INFO] Loss of {loss_name}: {loss_value}")

            except Exception as e:
                logger.error(f"[ERROR] Error in {loss_name} calculation: {e}")
                loss_list[loss_name]["loss_value"] = -1e6

        print("#" * 88)
        print(f"[DEBUG] loss_list: {loss_list}")
        print("#" * 88)

        total_loss = LossFactory.get_loss("total").calculate_loss(
            loss_list=loss_list)
        print(f"[DEBUG] total_loss: {total_loss}")

        try:
            from utils.plot import plot_multiple_curves_sim_vs_sim
            context, detail_info = plot_multiple_curves_sim_vs_sim(
                sim=current_sim,
                ori_data=baseline_sim_data,
                cycle_idxs=[1],
                is_plot=False,
                is_save=True,
                save_dir=f'./results/{time_stamp}/plot',
                model=configs.get("pybamm.EXP_SETTING.model_name", ""),
                param=configs.get("pybamm.EXP_SETTING.param_name", ""),
                id=f'sim_vs_sim_exp_{exp_idx}')
        except Exception as e:
            logger.warning(f"[WARNING] Failed to save comparison plot: {e}")

    except Exception as e:
        logger.error(f"[ERROR] Error in black_box_function_sim_vs_sim: {e}")

    finally:
        iteration_end_time = time.time()
        elapsed_time = iteration_end_time - iteration_start_time
        logger.info(f"[INFO] Total loss calculated: {total_loss}")
        logger.info(f"[INFO] loss_list: {loss_list}")
        logger.info(
            f"[INFO] Iteration completed. Time of this iteration: {elapsed_time:.2f} seconds."
        )

        return {
            "black_box_output": (-abs(total_loss), 0.0)
        }, loss_list, abs(total_loss)
