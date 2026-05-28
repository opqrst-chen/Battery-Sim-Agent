import time
import logging
import signal
import multiprocessing

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

# def solve_simulation(sim):
#     logger.info("Simulation solved successfully.")
#     try:
#         start_time = time.time()
#         sim.solve()
#         end_time = time.time()
#         return sim.solution, end_time - start_time
#     except Exception as e:
#         print(f"[Error] Solve failed: {e}")
#         return None, None

#     def timeout_handler(signum, frame):

#     old_handler = signal.signal(signal.SIGALRM, timeout_handler)
#     signal.alarm(timeout)

#     try:
#         logger.info("Simulation solved successfully.")
#         start_time = time.time()
#         end_time = time.time()
#         return sim.solution, end_time - start_time
#     except TimeoutError as e:
#         logger.error(f"[Timeout] {e}")
#         return None, None
#     except Exception as e:
#         logger.error(f"[Error] Solve failed: {e}")
#         return None, None
#     finally:
#         signal.alarm(0)
#         signal.signal(signal.SIGALRM, old_handler)

def _solve_worker(sim, result_queue):
    try:
        start_time = time.time()
        sim.solve()
        end_time = time.time()
        result_queue.put((sim.solution, end_time - start_time, None))
    except Exception as e:
        result_queue.put((None, None, e))

def solve_simulation(sim, timeout=180):
    logger.info("Starting simulation...")

    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_solve_worker,
                                      args=(sim, result_queue))
    process.start()

    process.join(timeout)

    if process.is_alive():
        logger.warning(
            f"Simulation exceeded {timeout} seconds. Terminating...")
        process.terminate()
        process.join()
        return None, None

    if not result_queue.empty():
        solution, elapsed_time, error = result_queue.get()
        if error:
            logger.error(f"[Error] Solve failed: {error}")
            return None, None
        logger.info("Simulation solved successfully.")
        return solution, elapsed_time
    else:
        logger.error("No result returned from simulation process.")
        return None, None
