import os
import json
import csv

def collect_results():
    results_dir = "results"

    with open(os.path.join(results_dir, "results.csv"), "w",
              encoding="utf-8") as f:
        f.write(
            "exp_index,timestamp,experiment_type,best_parameters,best_trial_index,best_total_loss,best_loss_list_capacity_rmse,best_loss_list_capacity_mape,best_loss_list_current_rmse,best_loss_list_current_mape,best_loss_list_voltage_rmse,best_loss_list_voltage_mape\n"
        )

    for entry in os.listdir(results_dir):
        exp_index = None
        with open(os.path.join(results_dir, "exp_setting.csv"),
                  "r",
                  encoding="utf-8") as f:
            exp_setting = csv.reader(f)
            for row in exp_setting:
                exp_index_in_csv = row[0]
                timestamp = row[1]
                if timestamp == entry:
                    exp_index = exp_index_in_csv
                    break

        root = os.path.join(results_dir, entry)

        if not os.path.isdir(root):
            continue

        files = os.listdir(root)
        # print(f"root:  {root}")
        # print(f"files: {files}")

        if "best_parameters_sim_vs_sim.json" in files:
            result_path = os.path.join(root, "best_parameters_sim_vs_sim.json")
            # try:
            with open(result_path, "r", encoding="utf-8") as f:
                print(f"{result_path}")
                result = json.load(f)
                timestamp = result["timestamp"]
                experiment_type = result["experiment_type"]
                best_parameters = result["best_parameters"]
                best_trial_index = result["best_trial_index"]
                best_total_loss = result["best_total_loss"]
                best_loss_list = result["best_loss_list"]
                # capacity
                best_loss_list_capacity = best_loss_list["capacity"][
                    "loss_value"]
                best_loss_list_capacity_rmse = best_loss_list_capacity[
                    "cycle_1"]["rmse"] if isinstance(
                        best_loss_list_capacity,
                        dict) else best_loss_list_capacity
                best_loss_list_capacity_mape = best_loss_list_capacity[
                    "cycle_1"]["mape"] if isinstance(
                        best_loss_list_capacity,
                        dict) else best_loss_list_capacity
                # current
                best_loss_list_current = best_loss_list["current"][
                    "loss_value"]
                best_loss_list_current_rmse = best_loss_list_current[
                    "cycle_1"]["rmse"] if isinstance(
                        best_loss_list_current,
                        dict) else best_loss_list_current
                best_loss_list_current_mape = best_loss_list_current[
                    "cycle_1"]["mape"] if isinstance(
                        best_loss_list_current,
                        dict) else best_loss_list_current
                # voltage
                best_loss_list_voltage = best_loss_list["voltage"][
                    "loss_value"]
                best_loss_list_voltage_rmse = best_loss_list_voltage[
                    "cycle_1"]["rmse"] if isinstance(
                        best_loss_list_voltage,
                        dict) else best_loss_list_voltage
                best_loss_list_voltage_mape = best_loss_list_voltage[
                    "cycle_1"]["mape"] if isinstance(
                        best_loss_list_voltage,
                        dict) else best_loss_list_voltage

                with open(os.path.join(results_dir, "results.csv"),
                          "a",
                          encoding="utf-8") as f:
                    f.write(
                        f"{exp_index},{timestamp},{experiment_type},{best_parameters},{best_trial_index},{best_total_loss},{best_loss_list_capacity_rmse},{best_loss_list_capacity_mape},{best_loss_list_current_rmse},{best_loss_list_current_mape},{best_loss_list_voltage_rmse},{best_loss_list_voltage_mape}\n"
                    )
            # except Exception as e:
            #     print(f"[ERROR] {result_path} - index [{exp_index}] - {e}")

def re_sort_results():
    results_dir = "results"
    results_file = os.path.join(results_dir, "results.csv")
    with open(results_file, "r", encoding="utf-8") as f:
        results = csv.reader(f)
        results_list = [row for row in results if 'exp_index' not in row]
        results_list.sort(key=lambda r: int(r[0]))

        results_resort_file = os.path.join(results_dir, "results_resort.csv")
        with open(results_resort_file, "w", encoding="utf-8") as f:
            f.write(
                "exp_index,timestamp,experiment_type,best_parameters,best_trial_index,best_total_loss,best_loss_list_capacity_rmse,best_loss_list_capacity_mape,best_loss_list_current_rmse,best_loss_list_current_mape,best_loss_list_voltage_rmse,best_loss_list_voltage_mape\n"
            )
            csv.writer(f).writerows(results_list)

def main():
    collect_results()
    re_sort_results()

if __name__ == "__main__":
    main()
