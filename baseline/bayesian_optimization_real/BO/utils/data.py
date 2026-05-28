import logging
import pickle

from utils.plot import plot_real_cycles, plot_real_capacity

logger = logging.getLogger(__name__)

def load_and_visualize_real_data(
        time_stamp: str,
        data_path: str = "../../real_world_data/CALCE_CS2_33.pkl"):
    real_data = load_battery_data(data_path=data_path)
    logger.info(
        f"[Info] Real cycle data keys: {real_data['cycle_data'][0].keys()}")

    formatted_real_data = real_data['formatted_cycle_data']
    plot_real_cycles(real_data=formatted_real_data,
                     cycle_index="all",
                     time_stamp=time_stamp)
    plot_real_capacity(real_data=real_data,
                       cycle_index="all",
                       time_stamp=time_stamp)

    try:
        plot_real_cycles(real_data=formatted_real_data,
                         cycle_index=[200, 400, 600],
                         time_stamp=time_stamp)
        plot_real_capacity(real_data=real_data,
                           cycle_index=[200, 400, 600],
                           time_stamp=time_stamp)
    except Exception as e:
        logger.error(f"[Error] {e}")

    return real_data

def load_battery_data(data_path="../../real_world_data/CALCE_CS2_33.pkl"):
    try:
        with open(data_path, 'rb') as f:
            real_data = pickle.load(f)

        if 'cycle_data' not in real_data:
            logger.error("[Error] Data does not contain 'cycle_data' field")
            return None

        logger.info(
            f"[Info] Loaded data, total cycles: {len(real_data['cycle_data'])}"
        )

        real_data['formatted_cycle_data'] = {
            f"cycle_{cycle_data['cycle_number']}": {
                'cycle_number':
                cycle_data['cycle_number'],
                'current_in_A':
                cycle_data['current_in_A'],
                'voltage_in_V':
                cycle_data['voltage_in_V'],
                'charge_capacity_in_Ah':
                cycle_data['charge_capacity_in_Ah'],
                'discharge_capacity_in_Ah':
                cycle_data['discharge_capacity_in_Ah'],
                'capacity_in_Ah':
                cycle_data['discharge_capacity_in_Ah'][-1],
                'time_in_s': [
                    time - min(cycle_data['time_in_s'])
                    for time in cycle_data['time_in_s']
                ],
                'temperature_in_C':
                cycle_data['temperature_in_C'],
                'internal_resistance_in_ohm':
                cycle_data['internal_resistance_in_ohm']
            }
            for cycle_data in real_data['cycle_data']
        }
        return real_data

    except Exception as e:
        logger.error(f"[Error] Failed to load data: {str(e)}")
        return None

def construct_sim_data(sim_sol):
    try:
        sim_data = {}

        # TODO: construct sim_data dict
        logger.info(f"[Info] cycle num of solution: {len(sim_sol.cycles)}")
        # logger.info(f"[Info] solution keys: {sim_sol.cycles[0].keys()}")
        for cycle in range(0, len(sim_sol.cycles)):
            cycle_str = f"cycle_{cycle}"
            sim_data[cycle_str] = {}
            sim_data[cycle_str]['capacity_in_Ah'] = sim_sol.cycles[cycle][
                "Discharge capacity [A.h]"].entries[-1]
            print(f"cycle_str: {cycle_str}: capacity_in_Ah: {sim_data[cycle_str]['capacity_in_Ah']}")
            sim_data[cycle_str]['time_in_s'] = sim_sol.cycles[cycle][
                "Time [s]"].entries
            sim_data[cycle_str][
                'current_in_A'] = -sim_sol.cycles[cycle]["Current [A]"].entries
            sim_data[cycle_str]['voltage_in_V'] = sim_sol.cycles[cycle][
                "Voltage [V]"].entries

            logger.info(f"[Info] [{cycle_str}]:")
            for key in [
                    'capacity_in_Ah', 'time_in_s', 'current_in_A',
                    'voltage_in_V'
            ]:
                val = sim_data[cycle_str][key]
                if hasattr(val, '__len__'):
                    logger.info(
                        f"[Info] [{cycle_str}] length of {key}: {len(val)}")
                else:
                    logger.info(f"[Info] [{cycle_str}] {key} is scalar: {val}")
        return sim_data
    except Exception as e:
        print(f"[Error] An error occurred: {e}")
        logger.error(f"[Error] An error occurred: {e}")
        return {}

#####################################################################
############## from call api all params new.ipynb ###################
#####################################################################

import numpy as np

def get_all_periods(current):
    # Find the indices where the array is equal to zero
    zero_indices = np.where(current == 0)[0]

    # Initialize a list to store the periods
    periods = []

    # Check if there are any zeros in the array
    if zero_indices.size > 0:
        # Initialize the start index of the first period
        start_idx = zero_indices[0]

        # Iterate through the zero indices to find contiguous periods
        for i in range(1, len(zero_indices)):
            if zero_indices[i] != zero_indices[i - 1] + 1:
                # End of a period
                end_idx = zero_indices[i - 1]
                periods.append((start_idx, end_idx))
                # Start of a new period
                start_idx = zero_indices[i]

        # Append the last period
        periods.append((start_idx, zero_indices[-1]))

    # Print the periods
    # print("Periods where values are equal to zero:", periods)
    new_periods = []
    for i in range(len(periods) - 1):
        new_periods.append(periods[i])
        new_periods.append([periods[i][1] + 1, periods[i + 1][0]])
    new_periods.append(periods[-1])
    return new_periods
