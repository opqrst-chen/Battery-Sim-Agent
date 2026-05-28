import logging
import os
import time
from tqdm import tqdm

from utils.exp import get_configs, init_experiment, save_to_jsonl
from utils.llm import call_llm_for_params_to_update, generate_degradation_message
from utils.data import load_and_visualize_real_data, load_battery_data, load_simulated_battery_data
from utils.plot import plot_sim_capacity
from pybamm_runner import build_simulation, solve_simulation
from memory import BatteryAgentMemory

logger = logging.getLogger(__name__)
SEARCH_KEYS=[
    'SEI reaction exchange current density [A.m-2]',
    'SEI resistivity [Ohm.m]',
    'SEI solvent diffusivity [m2.s-1]',
    'SEI open-circuit potential [V]',
    'Ambient temperature [K]',
    'Initial temperature [K]',
]

def degradation_pipeline(
    RESULTS_DIR: str,
    time_stamp: str,
    multi_modal=False,
    ori_settings: dict= None
):
    logger.info(f"[Info] Degradation pipeline starts.")

    
    params_jsonl_path, capacity_jsonl_path, all_messages_jsonl_path = init_experiment(
        RESULTS_DIR, time_stamp)

    params_to_search = {
        "Initial SEI thickness [m]": 4.5e-9,
        "Initial SEI on cracks thickness [m]": 5e-13,
        "SEI partial molar volume [m3.mol-1]": 1.3e-4,
        "SEI resistivity [Ohm.m]": 1.5e6,
        "SEI solvent diffusivity [m2.s-1]": 8e-21,
        "Bulk solvent concentration [mol.m-3]": 2636.0,
        "SEI reaction exchange current density [A.m-2]": 1e-11,
        "SEI open-circuit potential [V]": 0.4,
        "SEI electron conductivity [S.m-1]": 8.95e-14,
        "SEI lithium interstitial diffusivity [m2.s-1]": 1e-20,
        "Lithium interstitial reference concentration [mol.m-3]": 15.0,
        "EC initial concentration in electrolyte [mol.m-3]": 4541.0,
        "EC diffusivity [m2.s-1]": 2e-18,
        "SEI kinetic rate constant [m.s-1]": 1e-11,
        "SEI growth activation energy [J.mol-1]": 0.0,
        "Ratio of lithium moles to SEI moles": 5.0
    }

    from params import initial_params_for_first_cycle
    from pybamm_runner import simulate_capacity

    pybamm_configs = get_configs(config_type="pybamm", config_name="all")
    exp_configs = get_configs(config_type="exp", config_name="all")
    llm_configs = get_configs(config_type="llm", config_name="all")
    search_rounds = exp_configs['SEARCH_ROUNDS']
    cycle_idxs = exp_configs['INDEX_TO_SEARCH']
    if isinstance(ori_settings, dict):
        param_name = ori_settings['param_name']
        model_name = ori_settings['model_name']
        param_groups_list = [{}]
    else:
        param_name = pybamm_configs['DEFAULT_PARAMS_SET']
        model_name = pybamm_configs['DFN']
        param_groups_list = [initial_params_for_first_cycle.copy()]

    
    if isinstance(ori_settings, dict):
        ori_data = load_simulated_battery_data(ori_settings, cycle_len=cycle_idxs[-1]+1)
    else:
        ori_data = load_and_visualize_real_data(time_stamp)

    battery_agent_memory = BatteryAgentMemory(
        memory_path=os.path.join(RESULTS_DIR, "memory.jsonl"))

    return_loss = True
    start_time = time.time()

    for round_index in tqdm(
            range(1, search_rounds+1)):
        logger.info(f"[Info] Round {round_index} starts.")

        save_to_jsonl(list(param_groups_list), params_jsonl_path, mode="a")
        logger.info(f"[Info] Params to search saved to: {params_jsonl_path}")

        logger.info(f"[Info] Building simulation...")
        # new logic here
        cycle_description = ''
        for sub_idx, new_params in enumerate(param_groups_list):
            # log
            result = simulate_capacity( new_params,
                                        ori_data,
                                        param_name=param_name,
                                        model_name=model_name,
                                        target_capacity=None,
                                        cycle_idxs=cycle_idxs, 
                                        is_plot=True,
                                        is_save=True,
                                        save_dir=os.path.join(RESULTS_DIR, "plot"),
                                        id=f'round_{round_index}_sub_{sub_idx}',
                                        add_request=False,
                                        return_detail=True,
                                        return_loss=return_loss,
                                        ori_settings=ori_settings,
                                        search_keys=SEARCH_KEYS)
            if return_loss:
                is_success, context, capacity, detail_info, loss = result
            else:
                is_success, context, capacity, detail_info = result
            
            if is_success:
                logger.info(context)
                logger.info(f'The updated capacity is {capacity:.2f}')
                logger.info(detail_info)
                if return_loss:
                    logger.info(loss)
                
                # from utils.plot import plot_curves
                # plot_curves(current_params, cycle_idx=1, is_plot=True, is_save=True, model='SPMe', param='Ai2020')
            else:
                logger.error('Error message:')
                logger.error(context)
            cycle_description += context
            if return_loss:
                context_string = "The performance metrics are as follows:\n"
                for list_idx, cycle_idx in enumerate(cycle_idxs):
                    for key, value in loss[list_idx].items():
                        context_string += f"{key}: {value}\n"
                    cycle_description += f'Cycle {cycle_idx} loss: '
                    cycle_description += context_string
                # total_loss = loss["Q_mape"] + loss["I_mape"] + loss["V_mape"]
 

        from utils.llm import generate_first_cycle_message

        # TODO: Change to degradation message
        # round 1
        if llm_configs['PROMPT']['WITH_FIGURE']:
            image_path = os.path.join(RESULTS_DIR, "plot", f"round_{round_index}_sub_{sub_idx}.png")
        else:
            image_path = None

        if round_index == 1:
            protocols = f"The protocols are: [('Rest for 1 second', 'Charge at {ori_settings['charge_c_rate']}C until Vmax V', 'Rest for 1 second', 'Hold at Vmax V until C/20', 'Rest for 90 second', 'Discharge at {ori_settings['discharge_c_rate']}C until Vmin V', 'Rest for 90 second')]"
            messages = generate_first_cycle_message(
                    new_params,
                    cycle_description,
                    image_path=image_path,
                    protocols=protocols,
                    cycle_idxs=cycle_idxs,
                    parameter_set=param_name,
                    model_name=model_name,
                    multi_modal=multi_modal,
                    search_keys=SEARCH_KEYS,
                    round_index=round_index)
        # other round
        else:
            messages = generate_first_cycle_message(
                new_params, context,
                image_path=image_path,
                multi_modal=multi_modal,
                search_keys=SEARCH_KEYS,
                round_index=round_index)

        battery_agent_memory.add_messages_memory(messages)
        logger.info(f"[Info] Message generated.")

        # Call api to get next round params
        logger.info(f"[Info] Calling LLM for params to update...")
        llm_response, param_groups_list = call_llm_for_params_to_update(
            mode="first_cycle",
            messages=battery_agent_memory.get_messages_memory(),
            multi_vote_number=get_configs(config_type="exp",
                                          config_name="MULTI_VOTE_NUMBER"),
                                            all_messages_jsonl_path=all_messages_jsonl_path,
                                            time_stamp=time_stamp,
                                            search_keys=SEARCH_KEYS)
        print(llm_response)
        while (not param_groups_list) or (len(param_groups_list) == 0):
            current_time = time.time()
            duration = current_time - start_time
            logger.info(f'duration: {duration}')
            if duration > 10000:
                return
            time.sleep(3)
            logger.warning(f"[Warning] No valid parameter groups found.")
            # retry
            llm_response, param_groups_list = call_llm_for_params_to_update(
                mode="first_cycle",
                messages=battery_agent_memory.get_messages_memory(),
                multi_vote_number=get_configs(config_type="exp",
                                            config_name="MULTI_VOTE_NUMBER"),
                                                all_messages_jsonl_path=all_messages_jsonl_path,
                                                time_stamp=time_stamp,
                                                search_keys=SEARCH_KEYS)
            print(llm_response)
        battery_agent_memory.add_messages_memory([{
            "role": "assistant",
            "content": llm_response
        }])
        
        logger.info(f"[Info] LLM for params to update called.")
        logger.info(f"[Info] Params to search updated.")

    #     sim, param = build_simulation(
    #         # model_type="SPMe",
    #         # model_options=MODEL_OPTIONS,
    #         # params_set="Ai2020",
    #         # default_params=initial_params,
    #         params_to_update=params_to_search,
    #         # experiment=EXPERIMENT
    #     )
    #     logger.info(f"[Info] Simulation built.")

    #     logger.info(f"[Info] Solving simulation...")
    #     sim_sol, solve_time = solve_simulation(sim)
    #     logger.info(f"[Info] Solve time: {solve_time} seconds")
    #     logger.info(f"[Info] Simulation solved.")

    #     plot_sim_capacity(sim_sol,
    #                       research_round=round_index,
    #                       cycle_index="all",
    #                       time_stamp=time_stamp)
    #     plot_sim_capacity(
    #         sim_sol,
    #         research_round=round_index,
    #         cycle_index=get_configs(config_type="exp",
    #                                 config_name="INDEX_TO_SEARCH"),
    #         time_stamp=time_stamp)

    #     available_cycles = len(sim_sol.cycles)
    #     logger.info(f"[Info] Available cycles in solution: {available_cycles}")

    #     # plot_real_and_sim_cycles(real_data=real_data,
    #     #                          sim_data=sim_sol,
    #     #                          cycle_index="all",
    #     #                          time_stamp=time_stamp)
    #     # plot_real_and_sim_capacity(real_data=real_data,
    #     #                            sim_data=sim_sol,
    #     #                            cycle_index="all",
    #     #                            time_stamp=time_stamp)

    #     logger.info(f"[Info] Generating message...")
    #     messages = generate_degradation_message(
    #         real_data=real_data,
    #         sim_sol=sim_sol,
    #         params_to_search=params_to_search,
    #         index_to_search=get_configs(config_type="exp",
    #                                     config_name="INDEX_TO_SEARCH"),
    #         capacity_jsonl_path=capacity_jsonl_path)
    #     battery_agent_memory.add_messages_memory(messages)
    #     logger.info(f"[Info] Message generated.")

    #     logger.info(f"[Info] Calling LLM for params to update...")
    #     llm_response, params_to_update = call_llm_for_params_to_update(
    #         mode="degradation",
    #         messages=battery_agent_memory.get_messages_memory(),
    #         multi_vote_number=get_configs(config_type="exp",
    #                                       config_name="MULTI_VOTE_NUMBER"),
    #         all_messages_jsonl_path=all_messages_jsonl_path,
    #         time_stamp=time_stamp)
    #     battery_agent_memory.add_messages_memory([{
    #         "role": "assistant",
    #         "content": llm_response
    #     }])
    #     logger.info(f"[Info] LLM for params to update called.")

    #     params_to_search.update(params_to_update)
    #     logger.info(f"[Info] Params to search updated.")

    #     logger.info(f"[Info] Round {round_index} ends.")

    # logger.info(f"[Info] All rounds ends.")
