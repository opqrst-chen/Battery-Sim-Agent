import time
import pybamm
from utils.exp import get_configs, calculate_loss, log_experiment_csv
from utils.data import make_cccv
from params import initial_params, params_to_update
import os
from datetime import datetime
pybamm_configs = get_configs(config_type="pybamm", config_name="all")

SINGLE_CYCLE = tuple(pybamm_configs["SINGLE_CYCLE"])
EXPERIMENT = [SINGLE_CYCLE] * get_configs(config_type="exp",
                                          config_name="EXP_CYCLES")

MODEL_OPTIONS = pybamm_configs["MODEL_OPTIONS"]

SEARCH_KEYS= [
    'Negative particle radius [m]', 
    'Positive particle radius [m]', 
    'Negative electrode thickness [m]', 
    'Positive electrode thickness [m]', 
    'Negative electrode porosity', 
    'Positive electrode porosity', 
    'Negative electrode Bruggeman coefficient (electrolyte)', 
    'Positive electrode Bruggeman coefficient (electrolyte)', 
    'Separator thickness [m]'
]

# -------------------------------------------------
# -------------------------------------------------
def build_simulation(model_type="SPMe",
                     model_options=MODEL_OPTIONS,
                     params_set=pybamm_configs["DEFAULT_PARAMS_SET"],
                     default_params=initial_params,
                     params_to_update=None,
                     experiment=EXPERIMENT):
    if model_type.upper() == "DFN":
        model = pybamm.lithium_ion.DFN(options=model_options)
    else:
        model = pybamm.lithium_ion.SPMe(options=model_options)

    param = pybamm.ParameterValues(params_set)
    param.update(default_params, check_already_exists=False)

    param.update(params_to_update, check_already_exists=False)

    solver = pybamm.CasadiSolver(mode="safe", dt_max=60)

    sim = pybamm.Simulation(model,
                            parameter_values=param,
                            experiment=experiment,
                            solver=solver)
    sim.track_cycles = True

    return sim, param

def solve_simulation(sim):
    try:
        start_time = time.time()
        sim.solve()
        end_time = time.time()
        return sim.solution, end_time - start_time
    except Exception as e:
        print(f"[Error] Solve failed: {e}")
        return None, None

#####################################################################
############## from call api all params new.ipynb ###################
#####################################################################

def simulate_capacity(parameters,
                      ori_data,
                      param_name='Ai2020',
                      model_name='SPMe',
                      experiment=None,
                      target_capacity=None,
                      options=None,
                      cycle_idxs=[1],
                      is_plot=True,
                      is_save=False,
                      save_dir=None,
                      id='0',
                      add_request=False,
                      return_detail=False,
                      return_loss=False,
                      ori_settings=None,
                      search_keys=SEARCH_KEYS,
                      ):

    if not isinstance(options, dict):
        options = {
                "SEI": "reaction limited",  # Ensure SEI model is enabled
                "SEI film resistance": "distributed",
            }
    models = {
        'SPM': pybamm.lithium_ion.SPM(options=options),
        'SPMe': pybamm.lithium_ion.SPMe(options=options),
        'DFN': pybamm.lithium_ion.DFN(options=options),
    }
    model = models[model_name]
    
    param = pybamm.ParameterValues(param_name)
    params_Chen2020 = pybamm.ParameterValues('Chen2020')
    if param_name in ['Prada2013', 'ORegan2022']:
        append_params = {}
        for i in params_Chen2020:
            if i not in param:
                append_params[i] = params_Chen2020[i]
        param.update(append_params, check_already_exists=False)

    if parameters:
        # updata params
        param.update(parameters)

    log_params = {k: param[k] for k in search_keys if k in param}

    if isinstance(ori_settings, dict):
        v_min = param["Lower voltage cut-off [V]"]
        v_max = param["Upper voltage cut-off [V]"]
        experiment = make_cccv(charge_c_rate=ori_settings['charge_c_rate'], charge_v_cut=v_max, discharge_c_rate=ori_settings['discharge_c_rate'], discharge_v_cut=v_min, cycle_len=cycle_idxs[-1]+1)

    if not isinstance(experiment, pybamm.experiment.experiment.Experiment):
        # default protocol for CALCE battery
        experiment = pybamm.Experiment([(
            "Rest for 120 second",
            "Charge at C/2 until 4.2 V",
            "Rest for 120 second",
            "Hold at 4.2 V until 50 mA",
            "Rest for 90 second",
            "Discharge at C/2 until 2.7 V",
            "Rest for 90 second",
        )] * 2)

    # build simulation
    sim = pybamm.Simulation(model,
                            parameter_values=param,
                            experiment=experiment)
    
    try:
        sol = sim.solve(solver=pybamm.CasadiSolver(mode="safe", dt_max=60))
        from utils.plot import plot_multiple_curves
        from utils.data import load_battery_data, load_simulated_battery_data

        context, detail_info = plot_multiple_curves(
            sim,
            ori_data=ori_data,
            cycle_idxs=cycle_idxs,
            is_plot=is_plot,
            is_save=is_save,
            save_dir=save_dir,
            model=model_name,
            param=param_name,
            id=id,
            add_request=add_request)

        context += f'Current parameters are: {log_params}'

        for cycle_idx in cycle_idxs:
            # cycle_idx = cycle_idxs[0]
            capacity = sim.solution.cycles[cycle_idx]["Discharge capacity [A.h]"].entries[
                -1]
            if not target_capacity:
                target_capacity = ori_data[cycle_idx]["discharge_capacity_in_Ah"][-1]
            
            context += f'Cycle {cycle_idx} the updated simulated capacity is {capacity:.4f}, real data capacity is {target_capacity}Ah \n'

        parts = [True, context, capacity]

        if return_detail:
            parts.append(detail_info)

        if return_loss:
            if len(cycle_idxs) == 0:
                raise ValueError("cycle_idxs is empty; cannot compute loss.")
            all_loss_metrics = []
            for cycle_idx in cycle_idxs:  
                # compute only when requested; also safe-guard cycle_idxs
                # TODO: can we compute loss for multiple cycles at once?
                loss_metrics = calculate_loss(sim, ori_data, cycle_idx=cycle_idx)
                all_loss_metrics.append(loss_metrics)

            parts.append(all_loss_metrics)

            # dump loss
            loss_path = os.path.join(save_dir, "experiments.csv")
            settings = {k: param[k] for k in search_keys if k in param}
            current_timestamp = datetime.now().isoformat()

            # Initialize a dictionary to store sums
            sums = {key: 0 for key in all_loss_metrics[0].keys()}

            # Sum up each key's values
            for d in all_loss_metrics:
                for key in d:
                    sums[key] += d[key]

            # Calculate the mean for each key
            means = {key: sums[key] / len(all_loss_metrics) for key in sums}

            print("Means for each key:")
            for key, mean in means.items():
                print(f"{key}: {mean}")

            log_experiment_csv(loss_path, settings, means, experiment_id=id, notes=current_timestamp)

        return tuple(parts)
        
    except Exception as e:
        print(f"An error occurred: {e}")
        parts = [False, str(e), 0]

        if return_detail:
            detail_info = {}
            parts.append(detail_info)

        if return_loss:
            parts.append({})

        return tuple(parts)

