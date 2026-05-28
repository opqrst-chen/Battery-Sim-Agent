import os
import json
import yaml
import logging

logger = logging.getLogger(__name__)

def init_experiment(RESULTS_DIR: str, time_stamp: str):
    params_jsonl_path = os.path.join(RESULTS_DIR, "params.jsonl")
    capacity_jsonl_path = os.path.join(RESULTS_DIR, "capacity.jsonl")
    all_messages_jsonl_path = os.path.join(RESULTS_DIR, "all_messages.jsonl")

    exp_configs = get_configs(config_type="exp", config_name="all")
    llm_configs = get_configs(config_type="llm", config_name="all")
    save_to_jsonl(
        {
            "model_name": llm_configs["LLM_MODEL_NAME"],
            "temperature": llm_configs["TEMPERATURE"],
            "multi_vote_number": exp_configs["MULTI_VOTE_NUMBER"]
        },
        all_messages_jsonl_path,
        mode="w")
    return params_jsonl_path, capacity_jsonl_path, all_messages_jsonl_path

def save_to_jsonl(data, file_path, mode: str = "a"):
    with open(file_path, mode, encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')

def load_from_jsonl(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

_DEFAULT_CONFIG_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "configs")
)

def get_configs(config_type: str = "exp",
                config_name: str = "all",
                config_path: str = _DEFAULT_CONFIG_DIR):
    config_path = os.path.join(config_path, f"{config_type}.yaml")
    with open(config_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    if config_name == "all":
        return config
    else:
        return config.get(config_name, '')

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

import numpy as np
def calculate_loss(sim, target_cycle_data, cycle_idx=1):

    capacity = sim.solution.cycles[cycle_idx]["Discharge capacity [A.h]"].entries[-1]
    current = -sim.solution.cycles[cycle_idx]["Current [A]"].entries
    voltage = sim.solution.cycles[cycle_idx]["Terminal voltage [V]"].entries
    time = sim.solution.cycles[cycle_idx]["Time [s]"].entries
    voltage = interpolate_curve(time, voltage, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')
    current = interpolate_curve(time, current, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')

    target_capacity = target_cycle_data[cycle_idx]["discharge_capacity_in_Ah"][-1]
    target_current = np.array(target_cycle_data[cycle_idx]['current_in_A'])
    target_voltage = np.array(target_cycle_data[cycle_idx]['voltage_in_V'])
    target_time = np.array(target_cycle_data[cycle_idx]['time_in_s'])
    target_voltage = interpolate_curve(target_time, target_voltage, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')
    target_current = interpolate_curve(target_time, target_current, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')

    Q_rmse, Q_mape = rmse_mape([target_capacity], [capacity])
    

    I_rmse, I_mape = rmse_mape(target_current, current)
    V_rmse, V_mape = rmse_mape(target_voltage, voltage)

    loss = {
        "Q_rmse" : Q_rmse,
        "Q_mape" : Q_mape,
        "I_rmse" : I_rmse,
        "I_mape" : I_mape,
        "V_rmse" : V_rmse,
        "V_mape" : V_mape
    }
    # return Q_rmse, Q_mape, I_rmse, I_mape, V_rmse, V_mape
    return loss

import csv
import os

def log_experiment_csv(filepath, settings, results, experiment_id, notes=None):
    # Merge metadata + results into one flat dict row
    row = {"experiment_id": experiment_id, "notes": notes}
    row.update(settings)
    row.update(results)

    file_exists = os.path.isfile(filepath)

    with open(filepath, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()  # write header only once
        writer.writerow(row)

import re
import json
def extract_dict(response, src_type='json'):
    if src_type == 'json':
        data = json.loads(response)
        if len(data.keys()) == 1:
            for key, value in data.items():
                if type(value) == str:
                    match = re.search(r"```json(.*?)```", value, re.DOTALL)
                    json_str = match.group(1).strip() if match else None
                    # Parse JSON if found
                    data = json.loads(json_str) if json_str else None

    elif src_type != 'json':
        # Extract the JSON block
        match = re.search(r"```json(.*?)```", response, re.DOTALL)
        json_str = match.group(1).strip() if match else None

        # Parse JSON if found
        data = json.loads(json_str) if json_str else None

    # data.keys(), len(data["parameter_sets"])
    return data

from collections.abc import Mapping, Sequence

def gather_level_dicts(obj, search_keys):
    search_keys = set(search_keys)
    out = []

    def walk(x):
        # If x is a dict and contains any selected key, capture it and stop
        if isinstance(x, Mapping):
            if search_keys & set(x.keys()):
                out.append(x)
                return
            # otherwise, keep walking into its values
            for v in x.values():
                walk(v)
        elif isinstance(x, Sequence) and not isinstance(x, (str, bytes, bytearray)):
            for v in x:
                walk(v)
        # non-iterables are ignored

    walk(obj)
    return out