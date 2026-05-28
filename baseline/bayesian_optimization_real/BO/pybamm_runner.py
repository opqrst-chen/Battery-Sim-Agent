import time
import logging
import signal

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
    param.update(
        {
            "Nominal cell capacity [A.h]":
            configs.get("BO.battery.nominal_capacity")
        },
        check_already_exists=False)
    logger.info("Battery nominal capacity updated successfully.")

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

import pickle
from multiprocessing import Process, Queue
from concurrent.futures import ThreadPoolExecutor, TimeoutError

def _worker(sim, q):
    try:
        start_time = time.time()
        sim.solve()
        end_time = time.time()
        q.put((sim.solution, end_time - start_time))
    except Exception as e:
        logger.error(f"[Error] Solve failed in worker: {e}")
        q.put((None, None))

def _can_pickle(obj):
    try:
        pickle.dumps(obj)
        return True
    except Exception:
        return False

def solve_simulation(sim, timeout=300):
    if _can_pickle(sim):
        q = Queue()
        p = Process(target=_worker, args=(sim, q))
        p.start()
        p.join(timeout)

        if p.is_alive():
            logger.warning(f"Simulation timed out after {timeout} seconds.")
            p.terminate()
            p.join()
            return None, None

        if not q.empty():
            return q.get()
        else:
            return None, None
    else:
        def task():
            start_time = time.time()
            sim.solve()
            end_time = time.time()
            return sim.solution, end_time - start_time

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(task)
            try:
                return future.result(timeout=timeout)
            except TimeoutError:
                logger.warning(
                    f"Simulation timed out after {timeout} seconds.")
                return None, None
            except Exception as e:
                logger.error(f"[Error] Solve failed: {e}")
                return None, None
