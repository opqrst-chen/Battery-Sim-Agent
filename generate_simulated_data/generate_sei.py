import pybamm

# {# 1) Loss of Lithium Inventory (LLI) by continuous SEI growth
# 'options' = {"SEI": "reaction limited", "SEI film resistance": "distributed"}
# 'overrides' = {
#   "SEI reaction exchange current density [A.m-2]": {"op": "mul", "value": 2.0},  # faster growth
# }}, 
# {# 2) Impedance rise due to resistive SEI thickening
# 'options' = {"SEI": "reaction limited", "SEI film resistance": "distributed"}
# 'overrides' = {
#   "SEI resistivity [Ohm.m]": {"op": "mul", "value": 5.0} ,  # thicker/more resistive film
# }},
# {# 3) Calendar aging at rest (diffusion-limited SEI)
# 'options' = {"SEI": "reaction limited", "SEI film resistance": "distributed"}
# 'overrides' = {
#   "Outer SEI solvent diffusivity [m2.s-1]": {"op": "mul", "value": 0.2} ,  # transport bottleneck
# }},
# {# 4) Temperature-Stressed Calendar Aging
# 'options' = {"SEI": "reaction limited", "SEI film resistance": "distributed"}
# 'overrides' = {

#   "Cell temperature [K]": {"op": "set", "value": 318.15 },  # (45 °C)
#   "SEI reaction exchange current density [A.m-2]": {"op": "mul", "value": 2 },  # (45 °C)

# }},
# {#5) High-SOC accelerated aging (stronger driving force near top of charge)
# 'options' = {"SEI": "reaction limited", "SEI film resistance": "distributed"}
# 'overrides' = {
#   "Inner SEI open-circuit potential [V]":  {"op": "add", "value": -0.02 },  # more driving force at high SOC
# }}

def get_values(updated_params, overrides):
    param_name = 'Chen2020'
    update = {}
    for key, value in overrides.items():
        # print(key, value)
        base = updated_params[key]
        if value['op'] == 'mul':
            update[key]= base * value["value"]
        elif value['op'] == 'add':
            update[key]= base + value["value"]
        elif value['op'] == 'set':
            update[key]= value["value"]
    return update

override_list = [
    {
    "SEI reaction exchange current density [A.m-2]": {"op": "mul", "value": 2.0},  # faster growth
    },
    {
    "SEI resistivity [Ohm.m]": {"op": "mul", "value": 5.0} ,  # thicker/more resistive film
    },
    {
    "SEI solvent diffusivity [m2.s-1]": {"op": "mul", "value": 0.2} ,  # transport bottleneck
    },
    {
    "Initial temperature [K]": {"op": "set", "value": 318.15 },  # (45 °C)
    "Ambient temperature [K]": {"op": "set", "value": 318.15 },  # (45 °C)
    "SEI reaction exchange current density [A.m-2]": {"op": "mul", "value": 2 },  # (45 °C)
    },
    {
    "SEI open-circuit potential [V]":  {"op": "add", "value": -0.02 },  # more driving force at high SOC
    }
]

import matplotlib.pyplot as plt
from generate_params import make_cccv, run_experiment, calculate_diff, update_dict, save_yaml

if __name__ == "__main__":
    options = {"SEI": "reaction limited", "SEI film resistance": "distributed"}

    is_save = True
    is_plot = True
    model = pybamm.lithium_ion.DFN(options=options)
    to_save = {}
    model_name='DFN'
    param_name = 'Chen2020'
    param = pybamm.ParameterValues(param_name)
    v_min = param["Lower voltage cut-off [V]"]
    v_max = param["Upper voltage cut-off [V]"]
    # charge_c_rates = [0.2, 1, 2]
    # discharge_c_rates = [0.2, 1, 2]
    charge_c_rates = [1]
    discharge_c_rates = [1]
    for charge_c_rate in charge_c_rates:
        for discharge_c_rate in discharge_c_rates:
            for oid, overrides in enumerate(override_list):
                updated_params = param.copy()
                new_values = get_values(updated_params, overrides)
                updated_params.update(new_values, check_already_exists=False)
                # protocols = make_cc(charge_c_rate=charge_c_rate, charge_v_cut=v_max, discharge_c_rate=discharge_c_rate, discharge_v_cut=v_min, cycle_len=2)
                protocols = make_cccv(charge_c_rate=charge_c_rate, charge_v_cut=v_max, discharge_c_rate=discharge_c_rate, discharge_v_cut=v_min, cycle_len=200)
                # run_experiment(model, updated_params, protocols, cycle_idxs = [1], model_name='DFN', param_name=param_name, other_comment=f'({param_key}:{new_value} {discharge_c_rate}C)', axs=axs)
                # run the pybamm
                try:
                    fig, axs = plt.subplots(2, 1, figsize=(10, 10))
                    run_experiment(model, updated_params, protocols, cycle_idxs = [1, 99, 199], model_name='DFN', param_name=param_name, other_comment=f'(id:{oid} {charge_c_rate}-{discharge_c_rate}C)', axs=axs)
                    to_save = update_dict(to_save, oid, model_name, param_name, charge_c_rate, discharge_c_rate, new_values)

                    if is_save:
                        fig.savefig(f'./output/SEI/{oid}_{param_name}_{charge_c_rate}_{discharge_c_rate}C.png')
                    if is_plot:
                        plt.show()
                    else:
                        plt.close()
                except Exception as e:
                    print(f'{oid} {param_name} {charge_c_rate} {discharge_c_rate}C failed: {e}')

    new_yaml_file_path = './output/simulated_data_setting_SEI.yaml'
    save_yaml(to_save, new_yaml_file_path)
# python generate_sei.py