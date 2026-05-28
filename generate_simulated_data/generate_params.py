import pybamm
import matplotlib.pyplot as plt
import numpy as np
import pybamm as pb
from typing import Sequence, Union
import yaml
import os

Number = Union[int, float]

def save_yaml(data, new_yaml_file_path):
    # Write the modified data back to a YAML file
    with open(new_yaml_file_path, 'w') as yaml_file:
        yaml.dump(data, yaml_file, default_flow_style=False)

    print(f"Data has been modified and saved to {new_yaml_file_path}")

def read_yaml(yaml_file_path):
    with open(yaml_file_path, 'r') as yaml_file:
        data = yaml.safe_load(yaml_file)
    return data

def run_with(pkey, scale_or_delta,  pvals):
    # pvals = base_params.copy()
    if "porosity" in pkey or "Bruggeman" in pkey:
        # additive for porosity; direct set for Bruggeman if given as absolute
        if "porosity" in pkey:
            pvals[pkey] = max(0.2, min(0.6, pvals[pkey] + scale_or_delta))
        else:
            pvals[pkey] = scale_or_delta
    else:
        pvals[pkey] = pvals[pkey] * scale_or_delta
    return pvals[pkey]

def update_dict(to_save, id, model_name, param_name, charge_c_rate, discharge_c_rate, parameter_change):
    to_save[id] = {
        'model_name': model_name,
        'param_name' : param_name,
        'charge_c_rate' : charge_c_rate,
        'discharge_c_rate' : discharge_c_rate,
        'parameter_change' : parameter_change
    }
    return to_save

# ---------- Core protocols ----------
def make_cc(charge_c_rate: Number, charge_v_cut: Number, discharge_c_rate: Number, discharge_v_cut: Number, cycle_len: int = 1, duration: str | None = None):
    """
    CC charge or discharge until a voltage cut-off, optionally with a max duration.
    
    """

    return pb.Experiment([
        (
            "Rest for 1 second",
            f"Charge at {charge_c_rate}C until {charge_v_cut} V", 
            "Rest for 90 seconds",
            f"Discharge at {discharge_c_rate}C until {discharge_v_cut} V", 
            "Rest for 90 seconds",
        )
    ] * cycle_len)

def make_cccv(charge_c_rate: Number, charge_v_cut: Number, discharge_c_rate: Number, discharge_v_cut: Number, cycle_len: int = 1, rest: str | None = None):
    """
    Classic CCCV charge: CC to v_max, then hold until current threshold (e.g. 'C/20' or '50 mA').
    CV discharge: CC to voltage cut-off
    """
    return pb.Experiment([(
        "Rest for 1 second",
        f"Charge at {charge_c_rate}C until {charge_v_cut} V", 
        "Rest for 1 second",
        f"Hold at {charge_v_cut} V until C/20", 
        "Rest for 90 second",
        f"Discharge at {discharge_c_rate}C until {discharge_v_cut} V", 
        "Rest for 90 second"
        )
    ] * cycle_len)
    

def plot_figure(ax, x=None, y=None, title='', xlabel='', ylabel='', label=None, linestyle='-'):
    """
    Plot data on the given axes. x is optional.
    """
    if isinstance(x, np.ndarray) or isinstance(x, list):
        ax.plot(x, y, label=label , alpha=0.8, linewidth=1.5, linestyle=linestyle)
    else:
        ax.plot(y, label=label, alpha=0.8, linewidth=1.5, linestyle=linestyle)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()

def get_all_periods(current, delta=0.01):
    """
    Split different period by rest(current equals 0), and return periods index ranges
    """
    # Find the indices where the array is equal to zero
    zero_indices = np.where(np.abs(current - 0) < delta)[0]

    sign_change = np.sign(current[:-1]) != np.sign(current[1:])
    indices = np.where(sign_change)[0]
    append_idx = list(set(indices) - set(zero_indices))

    append_idx.sort()

    indices_to_insert = np.searchsorted(zero_indices, append_idx)
    # Insert the values at the found indices
    zero_indices = np.insert(zero_indices, indices_to_insert, append_idx)
    # print(zero_indices)

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
        new_periods.append([periods[i][1] + 1, periods[i+1][0]-1])
    new_periods.append(periods[-1])
    return new_periods

# Example: apply one combo to a copy of your baseline parameters
def apply_combo(pv, combo):
    pv = pv.copy()
    # shorthand
    mul = lambda k, m: pv.update({k: pv[k] * m})
    add = lambda k, d: pv.update({k: pv[k] + d})

    # particle radii
    mul("Negative particle radius [m]", combo["Rn"])
    mul("Positive particle radius [m]", combo["Rp"])

    # thicknesses
    mul("Negative electrode thickness [m]", combo["Ln"])
    mul("Positive electrode thickness [m]", combo["Lp"])

    # porosities (additive deltas; clamp if you enforce bounds)
    add("Negative electrode porosity", combo["εn"])
    add("Positive electrode porosity", combo["εp"])

    # Bruggeman (electrolyte) — set absolute values
    pv.update({"Negative electrode Bruggeman coefficient (electrolyte)": combo["bn"]})
    pv.update({"Positive electrode Bruggeman coefficient (electrolyte)": combo["bp"]})

    # separator
    mul("Separator thickness [m]", combo["Ls"])
    return pv

def map_combo(combo):
    combo_map = {
        "Rn" : "Negative particle radius [m]",
        "Rp" : "Positive particle radius [m]",
        "Ln" : "Negative electrode thickness [m]",
        "Lp" : "Positive electrode thickness [m]",
        "εn" : "Negative electrode porosity",
        "εp" : "Positive electrode porosity",
        "bn" : "Negative electrode Bruggeman coefficient (electrolyte)",
        "bp" : "Positive electrode Bruggeman coefficient (electrolyte)",
        "Ls" : "Separator thickness [m]",
    }
    return {combo_map[key]: value for key, value in combo.items() if key in combo_map}    

def run_experiment(model, param, experiment, cycle_idxs = [1], model_name='DFN', param_name='', other_comment='', axs=None):
    """
    Run the battery experiment simulation.
    Input model, param, experiment(protocols), the func would run the pybamm experiment, and plot curves.
    """
    # protocol
    detail_info = {}
    detail_info['simulated'] = {}
    sim = pybamm.Simulation(model, parameter_values=param, experiment=experiment)
    sol = sim.solve(solver=pybamm.CasadiSolver())
    
    context = ''
    for cycle_idx in cycle_idxs:
        context += f'Cycle {cycle_idx}: \n'
        time = sim.solution.cycles[cycle_idx]["Time [s]"].entries
        current = sim.solution.cycles[cycle_idx]["Current [A]"].entries
        voltage = sim.solution.cycles[cycle_idx]["Terminal voltage [V]"].entries
        capacity = sim.solution.cycles[cycle_idx]["Discharge capacity [A.h]"].entries

        discharge_mask = current>0
        charge_mask = current<0
        if not isinstance(axs, np.ndarray):
            fig, axs = plt.subplots(2, 1, figsize=(10, 10))

        linestyle = '--'
        plot_figure(axs[0], time-time[0], y=-current, title=f'{model_name} {param_name} Current vs Time {other_comment}', xlabel='Time [s]', ylabel='Current [A]', label=f'{cycle_idx}-{other_comment}', linestyle=linestyle)
        plot_figure(axs[1], time-time[0], y=voltage, title=f'{model_name} {param_name} Voltage vs Time {other_comment}', xlabel='Time [s]', ylabel='voltage [V]', label=f'{cycle_idx}-{other_comment}', linestyle=linestyle)
        # plot_figure(axs[0], time-time[0], y=-current, title=f'{model_name} {param_name} Current vs Time {other_comment}', xlabel='Time [s]', ylabel='Current [A]', label=f'{model_name}-{param_name}-{cycle_idx}-{other_comment}', linestyle=linestyle)
        # plot_figure(axs[1], time-time[0], y=voltage, title=f'{model_name} {param_name} Voltage vs Time {other_comment}', xlabel='Time [s]', ylabel='voltage [V]', label=f'{model_name}-{param_name}-{cycle_idx}-{other_comment}', linestyle=linestyle)
        # plot_figure(axs[2], time-time[0], y=capacity, title=f'{model} {param} Capacity vs Time', xlabel='Time [s]', ylabel='Discharge capacity [A.h]', label=f'{model}-{param}-{cycle_idx}')
        # plot_figure(axs[3], x=voltage[discharge_mask], y=capacity[discharge_mask], title=f'{model} {param} Capacity vs Voltage discharge', xlabel='voltage [V]', ylabel='Discharge capacity [A.h]', label=f'{model}-{param}-{cycle_idx}')

        periods = get_all_periods(current)
        # print(periods)
        if len(periods) == 7:
            period_names = ['first rest', 'Charge Constant Current', 'second rest', 'Charge Constant Voltage', 'third rest', 'Discharge Constant Current', 'fourth rest']
        elif len(periods) == 5:
            period_names = ['first rest', 'Charge Constant Current', 'second rest', 'Discharge Constant Current', 'third rest']
        for i in range(len(periods)):
            period_name = period_names[i]
            
            period = periods[i]
            if 'rest' in  period_name:
                continue
            # print(f'Simulated battery {period_name} last {(time[period[1]]- time[period[0]]):.2f} seconds')
            context += f'Simulated battery {period_name} last {(time[period[1]]- time[period[0]]):.2f} seconds \n '
            
            detail_info['simulated'][period_name] = {
                    'voltage': voltage[period[0]:period[1]+1],
                    'current': current[period[0]:period[1]+1],
                    'time': time[period[0]:period[1]+1],
                }
import numpy as np

def rmse_mape(y_true, y_pred):
    # Convert to numpy arrays
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    # Pad shorter array with zeros
    max_len = max(len(y_true), len(y_pred))
    y_true = np.pad(y_true, (0, max_len - len(y_true)), constant_values=np.nan)
    y_pred = np.pad(y_pred, (0, max_len - len(y_pred)), constant_values=np.nan)

    # Replace NaN with 0
    y_true = np.nan_to_num(y_true, nan=0.0)
    y_pred = np.nan_to_num(y_pred, nan=0.0)
    # RMSE
    rmse_val = np.sqrt(np.mean((y_true - y_pred) ** 2))

    # MAPE (exclude division by zero)
    nonzero_mask = y_true != 0
    if np.any(nonzero_mask):
        mape_val = np.mean(
            np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])
        ) * 100
    else:
        mape_val = np.nan  # undefined if all y_true == 0

    return rmse_val, mape_val

from scipy.interpolate import PchipInterpolator
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
def interpolate_curve(x, y, interpolate_num=None, is_plot=False, interpolate_method='PCHIP'):
    x = np.array(x)
    y = np.array(y)
    x = x-x[0]
    x, idx = np.unique(x, return_index=True)
    y = y[idx]

    if interpolate_num is None:
        interpolate_num = int(x.max())

    x_new = np.linspace(x.min(), x.max(), interpolate_num)

    if interpolate_method == 'PCHIP':
        f = PchipInterpolator(x, y)
        y_new = f(x_new)
    else:
        f = interp1d(x, y, kind="linear", bounds_error=False, fill_value="extrapolate")
        y_new = f(x_new)

    if is_plot:
        # plot
        plt.figure(figsize=(10, 8))
            
        plt.plot(x, y,  label="Original")
        plt.plot(x_new, y_new,label=interpolate_method)
        # plt.plot(x_new, y_new1,label="Interpolated (Linear)")

        plt.xlabel("Time [s]")
        plt.ylabel("Voltage [V]")
        plt.legend()
        plt.show()
    return y_new

def calculate_diff(ori_params, new_params, model, experiment, cycle_idx=1):
    sim = pybamm.Simulation(model, parameter_values=ori_params, experiment=experiment)
    sol = sim.solve(solver=pybamm.CasadiSolver())

    # get info
    capacity = sim.solution.cycles[cycle_idx]["Discharge capacity [A.h]"].entries[-1]
    current = -sim.solution.cycles[cycle_idx]["Current [A]"].entries
    voltage = sim.solution.cycles[cycle_idx]["Terminal voltage [V]"].entries
    time = sim.solution.cycles[cycle_idx]["Time [s]"].entries
    voltage = interpolate_curve(time, voltage, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')
    current = interpolate_curve(time, current, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')

    sim_new = pybamm.Simulation(model, parameter_values=new_params, experiment=experiment)
    sol = sim_new.solve(solver=pybamm.CasadiSolver())

    # get info
    capacity_new = sim_new.solution.cycles[cycle_idx]["Discharge capacity [A.h]"].entries[-1]
    current_new = -sim_new.solution.cycles[cycle_idx]["Current [A]"].entries
    voltage_new = sim_new.solution.cycles[cycle_idx]["Terminal voltage [V]"].entries
    time_new = sim_new.solution.cycles[cycle_idx]["Time [s]"].entries
    voltage_new = interpolate_curve(time_new, voltage_new, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')
    current_new = interpolate_curve(time_new, current_new, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')

    Q_rmse, Q_mape = rmse_mape([capacity], [capacity_new])
    I_rmse, I_mape = rmse_mape(current, current_new)
    V_rmse, V_mape = rmse_mape(voltage, voltage_new)

    loss = {
        "Q_rmse" : Q_rmse,
        "Q_mape" : Q_mape,
        "I_rmse" : I_rmse,
        "I_mape" : I_mape,
        "V_rmse" : V_rmse,
        "V_mape" : V_mape
    }

    # print(loss)
    return loss

models = {
    'SPM': pybamm.lithium_ion.SPM(options={
        "SEI": "reaction limited",  # Ensure SEI model is enabled
        "SEI film resistance": "distributed",
    }),
    'SPMe': pybamm.lithium_ion.SPMe(options={
        "SEI": "reaction limited",  # Ensure SEI model is enabled
        "SEI film resistance": "distributed",
    }),
    'DFN': pybamm.lithium_ion.DFN(options={
        "SEI": "reaction limited",  # Ensure SEI model is enabled
        "SEI film resistance": "distributed",
    }),
}

all_paramsets = [
    'Chen2020','ORegan2022','Prada2013','Ecker2015','Marquis2019',
]

to_sweep = {
    "Negative particle radius [m]": [0.5, 2.0],
    "Positive particle radius [m]": [0.5, 2.0],
    "Negative electrode thickness [m]": [0.75, 1.5],
    "Positive electrode thickness [m]": [0.75, 1.5],
    "Negative electrode porosity": [-0.05, +0.05],  # additive change
    "Positive electrode porosity": [-0.05, +0.05],
    "Negative electrode Bruggeman coefficient (electrolyte)": [1.5, 2.0, 2.5],
    "Positive electrode Bruggeman coefficient (electrolyte)": [1.3, 1.8, 2.3],
    "Separator thickness [m]": [0.7, 1.3],
}

model_name = 'DFN'
model = models[model_name]
id = 0
is_save = False
is_show = False
params_Chen2020 = pybamm.ParameterValues('Chen2020')

# Single change
to_save = {}

for param_name  in all_paramsets:
    print(param_name)
    # 
    # if param_name != 'ORegan2022' and param_name != 'Prada2013':
    #     continue

    param = pybamm.ParameterValues(param_name)
    params_Chen2020 = pybamm.ParameterValues('Chen2020')
    if param_name in ['Prada2013', 'ORegan2022']:
        append_params = {}
        for i in params_Chen2020:
            if i not in param:
                append_params[i] = params_Chen2020[i]
        param.update(append_params, check_already_exists=False)

    # change params 
    # single change
    v_min = param["Lower voltage cut-off [V]"]
    v_max = param["Upper voltage cut-off [V]"]

    charge_c_rates = [0.2, 1, 2]
    discharge_c_rates = [0.2, 1, 2]

    for charge_c_rate in charge_c_rates:
        for discharge_c_rate in discharge_c_rates:
            
            for param_key, change_list in to_sweep.items():
                print(param_key,change_list)
                # fig, axs = plt.subplots(2, 1, figsize=(10, 10))
                for scale_or_delta in change_list:
                    updated_params = param.copy()
                    new_value = run_with(param_key, scale_or_delta,  param.copy())
                    # print(new_value)
                    updated_params.update({param_key:new_value}, check_already_exists=False)
                    # print(updated_params[param_key])
                    
                    # protocols = make_cc(charge_c_rate=charge_c_rate, charge_v_cut=v_max, discharge_c_rate=discharge_c_rate, discharge_v_cut=v_min, cycle_len=2)
                    protocols = make_cccv(charge_c_rate=charge_c_rate, charge_v_cut=v_max, discharge_c_rate=discharge_c_rate, discharge_v_cut=v_min, cycle_len=2)
                    # run_experiment(model, updated_params, protocols, cycle_idxs = [1], model_name='DFN', param_name=param_name, other_comment=f'({param_key}:{new_value} {discharge_c_rate}C)', axs=axs)
                    # run the pybamm
                    try:
                        fig, axs = plt.subplots(2, 1, figsize=(10, 10))
                        run_experiment(model, updated_params, protocols, cycle_idxs = [1], model_name='DFN', param_name=param_name, other_comment=f'({param_key}:{new_value} {discharge_c_rate}C)', axs=axs)
                        # calculate difference of default setting and current setting, if small then skip
                        losses = calculate_diff(param, updated_params, model, protocols)
                        if losses['Q_mape'] < 1:
                            print(f'Skipped {param_name} {param_key}:{new_value} {charge_c_rate} {discharge_c_rate}C due to small difference {losses}')
                            continue
                        id += 1
                        to_save = update_dict(to_save, id, model_name, param_name, charge_c_rate, discharge_c_rate, {param_key: new_value})

                        if is_save:
                            fig.savefig(f'./output/simulated/{id}_{param_name}_{param_key}_{new_value}_{charge_c_rate}_{discharge_c_rate}C.png')
                    except Exception as e:
                        print(f'{param_name} {param_key}:{new_value} {charge_c_rate} {discharge_c_rate}C failed: {e}')
                        # skip this setting
                    # print(protocols)
                    
                # if is_save:
                #     fig.savefig(f'./output/simulated/{param_name}_{param_key}_{charge_c_rate}_{discharge_c_rate}C.png')
                if is_show:
                    plt.show()
                else:
                    plt.close()
    #             break
    #         break
    #     break
    # break            
new_yaml_file_path = './output/simulated_data_setting_single.yaml'
save_yaml(to_save, new_yaml_file_path)

# multi change

multi_combos = [
    # 1.Max-power, manuf.-plausible
	# Rationale: small particles + thin(ish) coatings + higher ε lowers both solid & ionic limits. 
    dict(Rn=0.7, Rp=0.7, Ln=0.85, Lp=0.9, εn=+0.04, εp=+0.04, bn=1.5, bp=1.5, Ls=0.9),
    # 2.Energy-leaning but still realistic (keep N/P)
    # Tip: if this hurts N/P, nudge Ln up/down to keep N/P ≈ 1.1.
	dict(Rn=1.0, Rp=1.0, Ln=1.10, Lp=1.25, εn=-0.02, εp=-0.03, bn=1.7, bp=1.7, Ls=1.0),
    # 3. Electrolyte-limited cathode (diagnostic)
	# Rationale: exposes cathode-side ionic starvation at high C.
    dict(Rn=1.0, Rp=1.0, Ln=1.0, Lp=1.25, εn=0, εp=-0.05, bn=1.6, bp=2.0, Ls=1.2),
    # 4.Solid-diffusion-limited (both sides)
    # Clean probe of Rp effects without transport confounders.
    dict(Rn=1.5, Rp=1.5, Ln=1.0, Lp=1.0, εn=0, εp=0, bn=1.7, bp=1.7, Ls=1.0),
    # 5.Anode-biased diffusion limit
    # Good for catching anode diffusion limitations and plating risk at higher C.
    dict(Rn=1.8, Rp=1.0, Ln=1.15, Lp=1.0, εn=0, εp=0, bn=1.7, bp=1.7, Ls=1.0),
    # 6.Cathode-biased diffusion limit
    dict(Rn=1.0, Rp=1.8, Ln=1.0, Lp=1.15, εn=0, εp=0, bn=1.7, bp=1.7, Ls=1.0),
    # Slightly thicker coatings to offset energy loss from higher ε.
    dict(Rn=1.0, Rp=1.0, Ln=1.10, Lp=1.10, εn=+0.06, εp=+0.06, bn=1.5, bp=1.5, Ls=1.0),
    # 8.Low-ε / high-tortuosity (worst-case ionic)
    # Stress test for ionic transport and heat generation.
    dict(Rn=1.0, Rp=1.0, Ln=1.0, Lp=1.0, εn=-0.06, εp=-0.06, bn=2.0, bp=2.0, Ls=1.2),

    # 9. Asymmetric particles (fast anode / slow cathode)
    dict(Rn=0.7, Rp=1.4, Ln=1.0, Lp=1.1, εn=0, εp=0, bn=1.7, bp=1.7, Ls=1.0),
    # 10. Asymmetric particles (slow anode / fast cathode)
    dict(Rn=1.4, Rp=0.7, Ln=1.1, Lp=1.0, εn=0, εp=0, bn=1.7, bp=1.7, Ls=1.0),
    # 11. Thin separator + thick electrodes (rate-assist)
    dict(Rn=1.0, Rp=1.0, Ln=1.20, Lp=1.25, εn=-0.02, εp=-0.03, bn=1.7, bp=1.7, Ls=0.85),
    # 12. Thick separator + low-ε (ionic choke)
    dict(Rn=1.0, Rp=1.0, Ln=1.10, Lp=1.10, εn=-0.04, εp=-0.04, bn=1.9, bp=1.9, Ls=1.5),
]

model_name = 'DFN'
model = models[model_name]
id = 0
is_save = False
is_show = False
params_Chen2020 = pybamm.ParameterValues('Chen2020')

to_save_multi = {}

for param_name  in all_paramsets:
    print(param_name)
    # if param_name != 'Chen2020':
    #     continue

    param = pybamm.ParameterValues(param_name)

    if param_name in ['Prada2013', 'ORegan2022']:
        append_params = {}
        for i in params_Chen2020:
            if i not in param:
                append_params[i] = params_Chen2020[i]
        param.update(append_params, check_already_exists=False)

    v_min = param["Lower voltage cut-off [V]"]
    v_max = param["Upper voltage cut-off [V]"]

    charge_c_rates = [0.2, 1, 2]
    discharge_c_rates = [0.2, 1, 2]

    for charge_c_rate in charge_c_rates:
        for discharge_c_rate in discharge_c_rates:
            for combo_idx, combo in enumerate(multi_combos):
                updated_params = apply_combo(param.copy(), combo)
                protocols = make_cccv(charge_c_rate=charge_c_rate, charge_v_cut=v_max, discharge_c_rate=discharge_c_rate, discharge_v_cut=v_min, cycle_len=2)
                # run_experiment(model, updated_params, protocols, cycle_idxs = [1], model_name='DFN', param_name=param_name, other_comment=f'({param_key}:{new_value} {discharge_c_rate}C)', axs=axs)
                # run the pybamm
                fig, axs = plt.subplots(2, 1, figsize=(10, 10))
                try:
                    run_experiment(model, updated_params, protocols, cycle_idxs = [1], model_name='DFN', param_name=param_name, other_comment=f'({discharge_c_rate}C)', axs=axs)
                    losses = calculate_diff(param, updated_params, model, protocols)
                    if losses['Q_mape'] < 1:
                        print(f'Skipped {param_name}{charge_c_rate} {discharge_c_rate}C due to small difference {losses}')
                        continue
                    id += 1
                    new_param = {k:v for k, v in updated_params.items() if k in to_sweep.keys()}
                    to_save_multi = update_dict(to_save_multi, id, model_name, param_name, charge_c_rate, discharge_c_rate, new_param)
                    if is_save:
                        fig.savefig(f'./output/multi/{id}_{param_name}_multi{combo_idx}_{charge_c_rate}_{discharge_c_rate}C.png')

                except:
                    print(f'{param_name}_multi{combo_idx} {charge_c_rate} {discharge_c_rate}C failed')

                # if is_save:
                #     fig.savefig(f'./output/simulated/{param_name}_multi{combo_idx}_{charge_c_rate}_{discharge_c_rate}C.png')
                if is_show:
                    plt.show()
                else:
                    plt.close()
   
new_yaml_file_path = './output/simulated_data_setting_multi.yaml'
save_yaml(to_save_multi, new_yaml_file_path)