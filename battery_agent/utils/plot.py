import logging
import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib import gridspec

logger = logging.getLogger(__name__)

def plot_real_cycles(real_data,
                     cycle_index: list[int] | str = "all",
                     current_or_voltage: str = "both",
                     figsize=(12, 8),
                     time_stamp=None):
    if cycle_index == "all":
        cycle_indices = sorted(
            [cycle_data['cycle_number'] for cycle_data in real_data.values()])
    else:
        cycle_indices = cycle_index

    cmap = cm.get_cmap('viridis', len(cycle_indices))

    norm = plt.Normalize(vmin=min(cycle_indices), vmax=max(cycle_indices))

    fig = plt.figure(figsize=figsize)
    gs = gridspec.GridSpec(2, 2, width_ratios=[1, 0.02], wspace=0.05)

    axes = [fig.add_subplot(gs[i, 0]) for i in range(2)]

    for i, cycle_idx in enumerate(cycle_indices):
        cycle_data = real_data[f"cycle_{cycle_idx}"]
        color = cmap(i)

        if current_or_voltage == "both":
            axes[0].plot(cycle_data['time_in_s'],
                         cycle_data['current_in_A'],
                         color=color)
            axes[1].plot(cycle_data['time_in_s'],
                         cycle_data['voltage_in_V'],
                         color=color)
        elif current_or_voltage == "current":
            axes[0].plot(cycle_data['time_in_s'],
                         cycle_data['current_in_A'],
                         color=color)
        elif current_or_voltage == "voltage":
            axes[1].plot(cycle_data['time_in_s'],
                         cycle_data['voltage_in_V'],
                         color=color)

    axes[0].set_ylabel('Current (A)')
    axes[1].set_ylabel('Voltage (V)')
    axes[1].set_xlabel('Time (s)')

    cbar_ax = fig.add_subplot(gs[:, 1])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax)
    cbar.set_label('Cycle Index')

    plt.subplots_adjust(right=0.85, wspace=0.1)

    save_path = f"./results/{time_stamp}/plot/real_cycles_{cycle_index}.png"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path)

    return fig

def plot_real_capacity(real_data,
                       cycle_index: list[int] | str = "all",
                       figsize=(12, 8),
                       time_stamp=None):
    all_cycle_capacities = []
    all_cycle_numbers = []

    if 'formatted_cycle_data' in real_data:
        for cycle_key, cycle_data in real_data['formatted_cycle_data'].items():
            if 'discharge_capacity_in_Ah' in cycle_data and cycle_data[
                    'discharge_capacity_in_Ah']:
                last_capacity = cycle_data['discharge_capacity_in_Ah'][-1]
                all_cycle_capacities.append(last_capacity)
                all_cycle_numbers.append(cycle_data['cycle_number'])
    elif 'cycle_data' in real_data:
        for cycle_data in real_data['cycle_data']:
            if 'discharge_capacity_in_Ah' in cycle_data and cycle_data[
                    'discharge_capacity_in_Ah']:
                last_capacity = cycle_data['discharge_capacity_in_Ah'][-1]
                all_cycle_capacities.append(last_capacity)
                all_cycle_numbers.append(cycle_data['cycle_number'])
    else:
        logger.error(
            "[Error] Data does not contain 'cycle_data' or 'formatted_cycle_data' field"
        )
        return None

    if not all_cycle_capacities:
        logger.error("[Error] No valid capacity data found")
        return None

    if cycle_index != "all":
        cycle_capacities = []
        cycle_numbers = []
        for cycle_idx in cycle_index:
            if cycle_idx in all_cycle_numbers:
                cycle_capacities.append(
                    all_cycle_capacities[all_cycle_numbers.index(cycle_idx)])
                cycle_numbers.append(cycle_idx)
            else:
                logger.error(f"[Error] Cycle {cycle_idx} not found in data")
                return None
    else:
        cycle_capacities = all_cycle_capacities
        cycle_numbers = all_cycle_numbers

    sorted_data = sorted(zip(cycle_numbers, cycle_capacities))
    cycle_numbers, cycle_capacities = zip(*sorted_data)

    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(cycle_numbers,
            cycle_capacities,
            'b-o',
            linewidth=2,
            markersize=3,
            markerfacecolor='white',
            markeredgewidth=2)

    ax.set_xlabel('Cycle Index', fontsize=12)
    ax.set_ylabel('Discharge Capacity (Ah)', fontsize=12)

    if cycle_index == "all":
        title = 'Battery Capacity Degradation Over All Cycles'
    else:
        title = f'Battery Capacity for Cycle {cycle_index}'

    ax.set_title(title, fontsize=14, fontweight='bold')

    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

    if len(cycle_numbers) <= 20:
        for i, (cycle_num,
                capacity) in enumerate(zip(cycle_numbers, cycle_capacities)):
            ax.annotate(f'{capacity:.3f}', (cycle_num, capacity),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha='center',
                        fontsize=8)

    plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)

    save_path = f"./results/{time_stamp}/plot/real_capacity_{cycle_index}.png"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    plt.savefig(save_path, dpi=300, bbox_inches='tight')

    if cycle_index == "all":
        logger.info(
            f"[Info] All cycles capacity degradation plot saved to: {save_path}"
        )
    else:
        logger.info(
            f"[Info] Cycle {cycle_index} capacity plot saved to: {save_path}")

    return fig

def plot_sim_capacity(sim_sol,
                      research_round: int,
                      cycle_index: list[int] | str = "all",
                      figsize=(12, 8),
                      time_stamp=None):
    all_cycle_capacities = []
    all_cycle_numbers = []

    if cycle_index == "all":
        cycle_index_to_plot = list(range(0, len(sim_sol.cycles)))
    else:
        cycle_index_to_plot = cycle_index

    for cycle_idx in cycle_index_to_plot:
        cycle_solution = sim_sol.cycles[cycle_idx]
        all_cycle_capacities.append(
            cycle_solution['Discharge capacity [A.h]'].entries[-1])
        all_cycle_numbers.append(cycle_idx)

    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(all_cycle_numbers,
            all_cycle_capacities,
            'b-o',
            linewidth=2,
            markersize=3,
            markerfacecolor='white',
            markeredgewidth=2)

    ax.set_xlabel('Cycle Index', fontsize=12)
    ax.set_ylabel('Discharge Capacity (Ah)', fontsize=12)

    ax.set_title(f'Battery Capacity for Cycle {cycle_index}',
                 fontsize=14,
                 fontweight='bold')

    if len(all_cycle_numbers) <= 20:
        for i, (cycle_num, capacity) in enumerate(
                zip(all_cycle_numbers, all_cycle_capacities)):
            ax.annotate(f'{capacity:.3f}', (cycle_num, capacity),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha='center',
                        fontsize=8)

    plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)

    save_path = f"./results/{time_stamp}/plot/sim_capacity_{research_round}_{cycle_index}.png"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig

def plot_real_and_sim_cycles(real_data,
                             sim_sol,
                             cycle_indices,
                             figsize=(12, 8),
                             time_stamp=None):
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)

    real_style = '-'
    sim_style = '--'

    for cycle_idx in cycle_indices:
        try:
            cycle_data = real_data[cycle_idx]
            time_real = [
                time_in_s - cycle_data['time_in_s'][0]
                for time_in_s in cycle_data['time_in_s']
            ]
            current_real = cycle_data['current_in_A']
            voltage_real = cycle_data['voltage_in_V']

            axes[0].plot(time_real,
                         current_real,
                         linestyle=real_style,
                         label=f'Real Cycle {cycle_idx}')
            axes[1].plot(time_real,
                         voltage_real,
                         linestyle=real_style,
                         label=f'Real Cycle {cycle_idx}')

        except (KeyError, IndexError) as e:
            print(
                f"Warning: Could not plot real data for cycle {cycle_idx}: {e}"
            )

        try:
            cycle_solution = sim_sol.cycles[cycle_idx]
            time_sim = cycle_solution["Time [s]"].entries
            time_sim = time_sim - time_sim[0]
            current_sim = -cycle_solution["Current [A]"].entries
            voltage_sim = cycle_solution["Terminal voltage [V]"].entries

            axes[0].plot(time_sim,
                         current_sim,
                         linestyle=sim_style,
                         label=f'Sim Cycle {cycle_idx}')
            axes[1].plot(time_sim,
                         voltage_sim,
                         linestyle=sim_style,
                         label=f'Sim Cycle {cycle_idx}')

        except (KeyError, IndexError, AttributeError) as e:
            print(
                f"Warning: Could not plot simulation data for cycle {cycle_idx}: {e}"
            )

    axes[0].set_ylabel('Current [A]')
    axes[0].set_title('Current vs Time: Real vs Simulation')
    axes[0].grid(True)

    axes[1].set_ylabel('Voltage [V]')
    axes[1].set_xlabel('Time [s]')
    axes[1].set_title('Voltage vs Time: Real vs Simulation')
    axes[1].grid(True)

    if len(cycle_indices) <= 5:
        axes[0].legend()
        axes[1].legend()
    else:
        axes[0].legend(loc='upper right', ncol=2, fontsize='small')
        axes[1].legend(loc='upper right', ncol=2, fontsize='small')

    plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)

    cycle_indices_str = "_".join(str(i) for i in cycle_indices)
    plt.savefig(
        f"./chkpts/{time_stamp}/degradation_compare_{cycle_indices_str}.png")

    return fig, axes

def plot_real_and_sim_capacity(real_data,
                               sim_sol,
                               cycle_indices,
                               figsize=(12, 8),
                               time_stamp=None):
    pass

#####################################################################
############## from call api all params new.ipynb ###################
#####################################################################

import os
import numpy as np
import pickle
import pandas as pd
import matplotlib.pyplot as plt

def plot_figure(ax,
                x=None,
                y=None,
                title='',
                xlabel='',
                ylabel='',
                label=None,
                linestyle='-'):
    if isinstance(x, np.ndarray) or isinstance(x, list):
        ax.plot(x, y, label=label, alpha=0.8, linewidth=1.5, linestyle=linestyle)
    else:
        ax.plot(y, label=label, alpha=0.8, linewidth=1.5, linestyle=linestyle)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()

def plot_curves(sim,
                cycle_idx=1,
                is_plot=True,
                is_save=False,
                model='',
                param=''):
    time = sim.solution.cycles[cycle_idx]["Time [s]"].entries
    current = sim.solution.cycles[cycle_idx]["Current [A]"].entries
    voltage = sim.solution.cycles[cycle_idx]["Terminal voltage [V]"].entries
    capacity = sim.solution.cycles[cycle_idx][
        "Discharge capacity [A.h]"].entries

    fig, axs = plt.subplots(4, 1, figsize=(10, 20))

    plot_figure(axs[0],
                x=time,
                y=-current,
                title=f'{model} {param} Current vs Time',
                xlabel='Time [s]',
                ylabel='Current [A]')
    plot_figure(axs[1],
                x=time,
                y=voltage,
                title=f'{model} {param} Voltage vs Time',
                xlabel='Time [s]',
                ylabel='voltage [V]')
    plot_figure(axs[2],
                x=time,
                y=capacity,
                title=f'{model} {param} Capacity vs Time',
                xlabel='Time [s]',
                ylabel='Discharge capacity [A.h]')
    plot_figure(axs[3],
                x=capacity,
                y=voltage,
                title=f'{model} {param} Capacity vs Voltage',
                xlabel='Discharge capacity [A.h]',
                ylabel='voltage [V]')

    plt.tight_layout()

    if is_save:
        fig.savefig(
            f'./pybamm_output/compare_models/{model}_{param}_{cycle_idx}.png')

    if is_plot:
        plt.show()
    else:
        plt.close()

def plot_multiple_curves(sim,
                         ori_data=None,
                         cycle_idxs=[1, 99, 299],
                         is_plot=True,
                         is_save=False,
                         save_dir='./pybamm_output/compare_models',
                         model='',
                         param='',
                         id='0',
                         add_request=True):
    fig, axs = plt.subplots(2, 1, figsize=(10, 10))

    context = f'{id} info:'
    detail_info = []
    for cycle_idx in cycle_idxs:
        cycle_detail = {
            'cycle_idx': cycle_idx,
            'simulated': {},
            'real': {},
        }
        time = sim.solution.cycles[cycle_idx]["Time [s]"].entries
        current = sim.solution.cycles[cycle_idx]["Current [A]"].entries
        voltage = sim.solution.cycles[cycle_idx][
            "Terminal voltage [V]"].entries
        capacity = sim.solution.cycles[cycle_idx][
            "Discharge capacity [A.h]"].entries

        discharge_mask = current > 0
        charge_mask = current < 0

        plot_figure(axs[0],
                    time - time[0],
                    y=-current,
                    title=f'{model} {param} Current vs Time',
                    xlabel='Time [s]',
                    ylabel='Current [A]',
                    label=f'{model}-{param}-{cycle_idx}',
                    linestyle='--')
        plot_figure(axs[1],
                    time - time[0],
                    y=voltage,
                    title=f'{model} {param} Voltage vs Time',
                    xlabel='Time [s]',
                    ylabel='voltage [V]',
                    label=f'{model}-{param}-{cycle_idx}',
                    linestyle='--')
        # plot_figure(axs[2], time-time[0], y=capacity, title=f'{model} {param} Capacity vs Time', xlabel='Time [s]', ylabel='Discharge capacity [A.h]', label=f'{model}-{param}-{cycle_idx}')
        # plot_figure(axs[3], x=voltage[discharge_mask], y=capacity[discharge_mask], title=f'{model} {param} Capacity vs Voltage discharge', xlabel='voltage [V]', ylabel='Discharge capacity [A.h]', label=f'{model}-{param}-{cycle_idx}')

        from utils.data import get_all_periods
        periods = get_all_periods(current)
        print(periods)
        period_names = [
            'first rest', 'Charge Constant Current', 'second rest',
            'Charge Constant Voltage', 'third rest',
            'Discharge Constant Current', 'fourth rest'
        ]
        for i in range(len(periods)):
            period_name = period_names[i]

            period = periods[i]
            if 'rest' in period_name:
                continue
            # print(f'Simulated battery {period_name} last {(time[period[1]]- time[period[0]]):.2f} seconds')
            context += f'Simulated battery cycle {cycle_idx} {period_name} last {(time[period[1]]- time[period[0]]):.2f} seconds \n '
            cycle_detail['simulated'][period_name] = {
                'voltage': voltage[period[0]:period[1] + 1],
                'current': current[period[0]:period[1] + 1],
                'time': time[period[0]:period[1] + 1],
            }

        if ori_data:
            time = np.array(ori_data[cycle_idx]['time_in_s'])
            current = np.array(ori_data[cycle_idx]['current_in_A'])
            voltage = np.array(ori_data[cycle_idx]['voltage_in_V'])
            # charge_capacity = np.array(
            #     ori_data[cycle_idx]['charge_capacity_in_Ah'])
            # discharge_capacity = np.array(
            #     ori_data[cycle_idx]['discharge_capacity_in_Ah'])
            # Qdlin = cycle_info[cycle_idx]['Qdlin']
            # discharge_mask = current < 0
            # charge_mask = current > 0

            # fig, axs = plt.subplots(4, 1, figsize=(10, 20))
            # print(voltage.shape, discharge_capacity.shape, discharge_mask.shape)
            plot_figure(axs[0],
                        x=time - time[0],
                        y=current,
                        title=f'{model} {param} Current vs Time',
                        xlabel='Time [s]',
                        ylabel='Current [A]',
                        label=f'origin-{cycle_idx}')
            plot_figure(axs[1],
                        x=time - time[0],
                        y=voltage,
                        title=f'{model} {param} Voltage vs Time',
                        xlabel='Time [s]',
                        ylabel='voltage [V]',
                        label=f'origin-{cycle_idx}')
            # plot_figure(axs[2], x=(time-time[0])[charge_mask], y=charge_capacity[charge_mask], title=f'{model} {param} Capacity vs Time', xlabel='Time [s]', ylabel='Discharge capacity [A.h]', label=f'origin-{cycle_idx}')
            # plot_figure(axs[3],  x=voltage[discharge_mask], y=discharge_capacity[discharge_mask], title=f'{model} {param} Capacity vs Voltage', xlabel='voltage [V]', ylabel='Discharge capacity [A.h]', label=f'origin-{cycle_idx}')
            # print('origin discharge capacity:', discharge_capacity[discharge_mask].max())
            from utils.data import get_all_periods
            periods = get_all_periods(current)

            if len(periods) == 7:
                period_names = ['first rest', 'Charge Constant Current', 'second rest', 'Charge Constant Voltage', 'third rest', 'Discharge Constant Current', 'fourth rest']
            elif len(periods) == 5:
                period_names = ['first rest', 'Charge Constant Current', 'second rest', 'Discharge Constant Current', 'third rest']
                
            for i in range(len(periods)):
                period_name = period_names[i]
                period = periods[i]
                if 'rest' in period_name:
                    continue
                # print(f'Real battery {period_name} last {(time[period[1]]- time[period[0]]):.2f} seconds')
                context += f'Real battery cycle {cycle_idx} {period_name} last {(time[period[1]]- time[period[0]]):.2f} seconds \n '
                cycle_detail['real'][period_name] = {
                    'voltage': voltage[period[0]:period[1] + 1],
                    'current': current[period[0]:period[1] + 1],
                    'time': time[period[0]:period[1] + 1],
                }
        detail_info.append(cycle_detail)
    # print('Could you describe the problem and analyze problem with the corresponding current and voltage curves then output the next updated params ')
    if add_request == True:
        context += 'Could you describe the problem and analyze problem with the corresponding current and voltage curves then output the next updated params, you just need to updated these params, and not change other params '
    plt.tight_layout()
    if is_save:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        fig.savefig(f'{save_dir}/{id}.png')

    if is_plot:
        plt.show()
    else:
        plt.close()

    return context, detail_info
