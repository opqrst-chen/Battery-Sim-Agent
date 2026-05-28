import os
import argparse
import yaml

def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, default=1)
    parser.add_argument(
        "--setting_file",
        type=str,
        default=
        "../../generate_simulated_data/output/simulated_data_setting_single.yaml"
    )  # noqa: E501
    parser.add_argument("--config_dir", type=str, default="configs")
    # parser.add_argument("--bounds_factor", type=float, default=0.2)
    return parser.parse_args()

def update_configs(index, setting_file, config_dir):
    try:
        with open(setting_file, "r", encoding="utf-8") as f:
            settings = yaml.safe_load(f)

        update_data = settings[index]
        update_data["exp_index"] = index
        charge_c_rate = update_data["charge_c_rate"]
        discharge_c_rate = update_data["discharge_c_rate"]
        model_name = update_data["model_name"]
        param_name = update_data["param_name"]
        parameter_change = update_data["parameter_change"]
        

        # update pybamm.yaml
        pybamm_template_config_path = os.path.join(config_dir,
                                                   "pybamm_template.yaml")
        with open(pybamm_template_config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        config_data["MODEL_NAME"] = model_name
        config_data["DEFAULT_PARAMS_SET"] = param_name

        import pybamm
        param = pybamm.ParameterValues(param_name)

        v_min = param["Lower voltage cut-off [V]"]
        v_max = param["Upper voltage cut-off [V]"]

        updated_steps = []
        for step in config_data["SINGLE_CYCLE"]:
            step = step.format(charge_c_rate=charge_c_rate,
                               discharge_c_rate=discharge_c_rate,
                               v_min=v_min,
                               v_max=v_max)
            updated_steps.append(step)
        config_data["SINGLE_CYCLE"] = updated_steps

        config_data["EXP_INDEX"] = index
        config_data["SETTING_FILE"] = setting_file
        config_data["EXP_SETTING"] = update_data

        pybamm_config_path = os.path.join(config_dir, "pybamm.yaml")
        with open(pybamm_config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True)

        # update exp.yaml
        exp_config_path = os.path.join(config_dir, "exp.yaml")
        with open(exp_config_path, "r", encoding="utf-8") as f:
            exp_config_data = yaml.safe_load(f)

        exp_config_data["SIM_VS_SIM"]["parameter_change"] = parameter_change
        exp_config_data["SIM_VS_SIM"]["baseline_sim_id"] = index
        exp_config_data["SIM_VS_SIM"]["baseline_sim_config"] = setting_file

        # print(f"[DEBUG] config_data['pbounds']: {config_data['pbounds']}")
        with open(exp_config_path, "w", encoding="utf-8") as f:
            yaml.dump(exp_config_data, f, allow_unicode=True)
    except Exception as e:
        print(f"Error in update_configs: {e}")
        return False
    return True

def main():
    args = arg_parser()
    update_configs(
        args.index,
        args.setting_file,
        args.config_dir,
    )

# if __name__ == "__main__":
#     # test
#     index = 3
#     setting_file = "../../generate_simulated_data/output/simulated_data_setting_single.yaml"  # noqa: E501
#     config_dir = "configs"
#     bounds_factor = 0.2
#     update_flag = update_configs(index, setting_file, config_dir,
#                                  bounds_factor)
#     print(f"Update configs: {update_flag}")

if __name__ == "__main__":
    main()
