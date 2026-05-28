import logging
import pickle
import pybamm
from typing import Sequence, Union
Number = Union[int, float]

from utils.plot import plot_real_cycles, plot_real_capacity

logger = logging.getLogger(__name__)

def load_and_visualize_real_data(time_stamp: str):
    real_data = load_battery_data()
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

def load_battery_data(data_path="./real_world_data/CALCE_CS2_33.pkl"):
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

def assign_variables_from_dict(d):
    for key, value in d.items():
        exec(f"{key} = {value}", globals())

def make_cccv(charge_c_rate: Number, charge_v_cut: Number, discharge_c_rate: Number, discharge_v_cut: Number, cycle_len: int = 1, rest: str | None = None):
    """
    Classic CCCV charge: CC to v_max, then hold until current threshold (e.g. 'C/20' or '50 mA').
    CV discharge: CC to voltage cut-off
    """
    return pybamm.Experiment([(
        "Rest for 1 second",
        f"Charge at {charge_c_rate}C until {charge_v_cut} V", 
        "Rest for 1 second",
        f"Hold at {charge_v_cut} V until C/20", 
        "Rest for 90 second",
        f"Discharge at {discharge_c_rate}C until {discharge_v_cut} V", 
        "Rest for 90 second"
        )
    ] * cycle_len)
    

import pybamm

def load_simulated_battery_data(settings, cycle_len=2):
    """
    Load simulated battery data from the given settings.
    charge_c_rate, discharge_c_rate, model_name, param_name, parameter_change
    """
    options = {
        "SEI": "reaction limited",  # Ensure SEI model is enabled
        "SEI film resistance": "distributed",
    }
    models = {
        'SPM': pybamm.lithium_ion.SPM(options=options),
        'SPMe': pybamm.lithium_ion.SPMe(options=options),
        'DFN': pybamm.lithium_ion.DFN(options=options),
    }
    model = models[settings['model_name']]

    param = pybamm.ParameterValues(settings['param_name'])
    params_Chen2020 = pybamm.ParameterValues('Chen2020')
    if settings['param_name'] in ['Prada2013', 'ORegan2022']:
        append_params = {}
        for i in params_Chen2020:
            if i not in param:
                append_params[i] = params_Chen2020[i]
        param.update(append_params, check_already_exists=False)

    v_min = param["Lower voltage cut-off [V]"]
    v_max = param["Upper voltage cut-off [V]"]

    param.update(settings['parameter_change'], check_already_exists=False)
    # protocols = make_cc(charge_c_rate=charge_c_rate, charge_v_cut=v_max, discharge_c_rate=discharge_c_rate, discharge_v_cut=v_min, cycle_len=cycle_len)
    experiment = make_cccv(charge_c_rate=settings['charge_c_rate'], charge_v_cut=v_max, discharge_c_rate=settings['discharge_c_rate'], discharge_v_cut=v_min, cycle_len=cycle_len)

    sim = pybamm.Simulation(model, parameter_values=param, experiment=experiment)
    sol = sim.solve(solver=pybamm.CasadiSolver(mode="safe", dt_max=60))
    
    cycle_data = []
    for cycle_idx in range(cycle_len):
        cycle_info ={}
        cycle_info['time_in_s'] = sim.solution.cycles[cycle_idx]["Time [s]"].entries
        cycle_info['current_in_A'] = -sim.solution.cycles[cycle_idx]["Current [A]"].entries
        cycle_info['voltage_in_V'] = sim.solution.cycles[cycle_idx]["Terminal voltage [V]"].entries
        cycle_info['discharge_capacity_in_Ah'] = sim.solution.cycles[cycle_idx]["Discharge capacity [A.h]"].entries
    
        cycle_data.append(cycle_info)
    return cycle_data

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
            if zero_indices[i] != zero_indices[i-1] + 1:
                # End of a period
                end_idx = zero_indices[i-1]
                periods.append((start_idx, end_idx))
                # Start of a new period
                start_idx = zero_indices[i]
        
        # Append the last period
        periods.append((start_idx, zero_indices[-1]))

    # Print the periods
    # print("Periods where values are equal to zero:", periods)
    new_periods = []
    for i in range(len(periods)-1):
        new_periods.append(periods[i])
        new_periods.append([periods[i][1] + 1, periods[i+1][0]])
    new_periods.append(periods[-1])
    return new_periods

