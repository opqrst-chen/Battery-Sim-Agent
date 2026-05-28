import time
import logging

import pybamm

logger = logging.getLogger(__name__)

def build_simulation(
    configs,
    parameters: dict = None,
    fixed_parameters: dict = None,
):
    pybamm_configs = configs.get("pybamm")

    SINGLE_CYCLE = tuple(pybamm_configs["SINGLE_CYCLE"])
    EXPERIMENT = [SINGLE_CYCLE] * configs.get("exp.EXP_CYCLES")

    model_type = pybamm_configs["MODEL_NAME"]
    MODEL_OPTIONS = pybamm_configs["MODEL_OPTIONS"]

    if model_type.upper() == "DFN":
        model = pybamm.lithium_ion.DFN(options=MODEL_OPTIONS)
    else:
        model = pybamm.lithium_ion.SPMe(options=MODEL_OPTIONS)
    logger.info("Battery model selected successfully.")

    param = pybamm.ParameterValues(pybamm_configs["DEFAULT_PARAMS_SET"])
    logger.info("Battery default parameters initialized successfully.")

    if fixed_parameters is not None:
        param.update(fixed_parameters, check_already_exists=False)

    param.update(parameters, check_already_exists=False)
    logger.info("Battery parameters updated successfully.")
    
    params_Chen2020 = pybamm.ParameterValues('Chen2020')
    if pybamm_configs["DEFAULT_PARAMS_SET"] in ['Prada2013', 'ORegan2022']:
        append_params = {}
        for i in params_Chen2020:
            if i not in param:
                append_params[i] = params_Chen2020[i]
        param.update(append_params, check_already_exists=False)

    solver = pybamm.CasadiSolver(mode="safe", dt_max=60)
    logger.info("Solver initialized successfully.")

    logger.info("Creating simulation...")
    logger.info(f"Model: {model}")
    logger.info(f"Parameter values: {param}")
    logger.info(f"Experiment: {EXPERIMENT}")
    logger.info(f"Solver: {solver}")
    sim = pybamm.Simulation(model=model,
                            parameter_values=param,
                            experiment=EXPERIMENT,
                            solver=solver)
    sim.track_cycles = True
    logger.info("Simulation created successfully.")

    return sim, param

def solve_simulation(sim):
    logger.info("Simulation solved successfully.")
    try:
        start_time = time.time()
        sim.solve()
        end_time = time.time()
        return sim.solution, end_time - start_time
    except Exception as e:
        print(f"[Error] Solve failed: {e}")
        return None, None
