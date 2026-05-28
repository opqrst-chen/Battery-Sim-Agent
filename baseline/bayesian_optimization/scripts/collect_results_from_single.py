import os
import json
import csv
import yaml

def collect_results_from_single():
    results_dir = "results"

    header = (
        "exp_index,timestamp,experiment_type,best_trial_index,"
        "best_total_loss,best_loss_list_capacity_rmse,best_loss_list_capacity_mape,"
        "best_loss_list_current_rmse,best_loss_list_current_mape,"
        "best_loss_list_voltage_rmse,best_loss_list_voltage_mape,'Negative_particleNegative_particle_radius_m', 'Positive_particle_radius_m', 'Negative_electrode_thickness_m', 'Positive_electrode_thickness_m', 'Negative_electrode_porosity', 'Positive_electrode_porosity', 'Negative_electrode_Bruggeman_coefficient_electrolyte', 'Positive_electrode_Bruggeman_coefficient_electrolyte', 'Separator_thickness_m',changed_parameters,complete\n"
    )

    output_path = os.path.join(results_dir, "results_from_single.csv")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)

    # Build timestamp -> exp_index map from exp_setting.csv
    timestamp_to_exp_index = {}
    exp_setting_path = os.path.join(results_dir, "exp_setting.csv")
    if os.path.exists(exp_setting_path):
        with open(exp_setting_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0] == "exp_index":
                    continue
                # CSV columns: exp_index,time_stamp
                if len(row) >= 2:
                    timestamp_to_exp_index[row[1]] = row[0]

    # Iterate first-level entries in results directory
    for entry in os.listdir(results_dir):
        root = os.path.join(results_dir, entry)

        # Only consider first-level subdirectories (timestamp folders)
        if not os.path.isdir(root):
            continue

        records_file = os.path.join(root, "bo_sim_vs_sim_records.jsonl")
        if not os.path.exists(records_file):
            continue

        line_count = 0
        best_record = None
        best_total_loss = None

        # Read JSONL, count lines, and find best (min) total_loss
        with open(records_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                line_count += 1
                try:
                    record = json.loads(line)
                except Exception:
                    continue

                total_loss = record.get("total_loss")
                if total_loss == -1000000.0:
                    continue
                if best_total_loss is None or (total_loss is not None and
                                               total_loss < best_total_loss):
                    best_total_loss = total_loss
                    best_record = record

        if best_record is None:
            continue

        # Determine fields
        exp_index = timestamp_to_exp_index.get(entry, "")
        timestamp = entry
        experiment_type = best_record.get("experiment_type", "")
        best_parameters = best_record.get("parameters", {})
        best_trial_index = best_record.get("exp_idx", "")
        Negative_particleNegative_particle_radius_m = best_parameters.get(
            "Negative_particleNegative_particle_radius_m", "")
        Positive_particle_radius_m = best_parameters.get(
            "Positive_particle_radius_m", "")
        Negative_electrode_thickness_m = best_parameters.get(
            "Negative_electrode_thickness_m", "")
        Positive_electrode_thickness_m = best_parameters.get(
            "Positive_electrode_thickness_m", "")
        Negative_electrode_porosity = best_parameters.get(
            "Negative_electrode_porosity", "")
        Positive_electrode_porosity = best_parameters.get(
            "Positive_electrode_porosity", "")
        Negative_electrode_Bruggeman_coefficient_electrolyte = best_parameters.get(
            "Negative_electrode_Bruggeman_coefficient_electrolyte", "")
        Positive_electrode_Bruggeman_coefficient_electrolyte = best_parameters.get(
            "Positive_electrode_Bruggeman_coefficient_electrolyte", "")
        Separator_thickness_m = best_parameters.get("Separator_thickness_m",
                                                    "")

        # Extract losses (handle both dict and scalar cases like -1000000.0)
        loss_list = best_record.get("loss_list", {})

        # capacity
        cap_value = (loss_list.get("capacity", {}) or {}).get("loss_value")
        if isinstance(cap_value, dict):
            cap_cycle_1 = (cap_value.get("cycle_1", {}) or {})
            cap_rmse = cap_cycle_1.get("rmse", "")
            cap_mape = cap_cycle_1.get("mape", "")
        else:
            cap_rmse = cap_value
            cap_mape = cap_value

        # current
        cur_value = (loss_list.get("current", {}) or {}).get("loss_value")
        if isinstance(cur_value, dict):
            cur_cycle_1 = (cur_value.get("cycle_1", {}) or {})
            cur_rmse = cur_cycle_1.get("rmse", "")
            cur_mape = cur_cycle_1.get("mape", "")
        else:
            cur_rmse = cur_value
            cur_mape = cur_value

        # voltage
        vol_value = (loss_list.get("voltage", {}) or {}).get("loss_value")
        if isinstance(vol_value, dict):
            vol_cycle_1 = (vol_value.get("cycle_1", {}) or {})
            vol_rmse = vol_cycle_1.get("rmse", "")
            vol_mape = vol_cycle_1.get("mape", "")
        else:
            vol_rmse = vol_value
            vol_mape = vol_value

        complete = line_count

        changed_parameters = None
        changed_parameters_file = os.path.join(root, "configs", "exp.yaml")
        with open(changed_parameters_file, "r", encoding="utf-8") as f:
            exp_configs = yaml.safe_load(f)
            changed_parameters = exp_configs.get("SIM_VS_SIM", {}).get(
                "parameter_change", {})

        # Write one line to CSV
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(
                f"{exp_index},{timestamp},{experiment_type},{best_trial_index},{best_total_loss},"
                f"{cap_rmse},{cap_mape},{cur_rmse},{cur_mape},{vol_rmse},{vol_mape},{Negative_particleNegative_particle_radius_m},{Positive_particle_radius_m},{Negative_electrode_thickness_m},{Positive_electrode_thickness_m},{Negative_electrode_porosity},{Positive_electrode_porosity},{Negative_electrode_Bruggeman_coefficient_electrolyte},{Positive_electrode_Bruggeman_coefficient_electrolyte},{Separator_thickness_m},{changed_parameters},{complete}\n"
            )

def re_sort_results():
    results_dir = "results"
    results_file = os.path.join(results_dir, "results_from_single.csv")
    with open(results_file, "r", encoding="utf-8") as f:
        results = csv.reader(f)
        results_list = [row for row in results if 'exp_index' not in row]
        results_list.sort(key=lambda r: int(r[0]))

        results_resort_file = os.path.join(results_dir,
                                           "results_resort_from_single.csv")
        with open(results_resort_file, "w", encoding="utf-8") as f:
            f.write(
                "exp_index,timestamp,experiment_type,best_trial_index,best_total_loss,best_loss_list_capacity_rmse,best_loss_list_capacity_mape,best_loss_list_current_rmse,best_loss_list_current_mape,best_loss_list_voltage_rmse,best_loss_list_voltage_mape,'Negative_particleNegative_particle_radius_m', 'Positive_particle_radius_m', 'Negative_electrode_thickness_m', 'Positive_electrode_thickness_m', 'Negative_electrode_porosity', 'Positive_electrode_porosity', 'Negative_electrode_Bruggeman_coefficient_electrolyte', 'Positive_electrode_Bruggeman_coefficient_electrolyte', 'Separator_thickness_m',changed_parameters,complete\n"
            )
            csv.writer(f).writerows(results_list)

def main():
    collect_results_from_single()
    re_sort_results()

if __name__ == "__main__":
    main()
