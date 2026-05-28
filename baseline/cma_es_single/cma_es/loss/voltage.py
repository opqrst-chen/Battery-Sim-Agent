from collections import defaultdict
from typing import Dict, Any
import logging
import numpy as np

from .base import BaseLoss

logger = logging.getLogger(__name__)

class VoltageLoss(BaseLoss):

    def __init__(self):
        super().__init__("voltage")

    def calculate_loss(self, real_data: Dict[str, Any],
                       sim_data: Dict[str, Any], **kwargs) -> float:
        logger.info(f"[INFO] Calculating voltage loss...")
        print(f"[INFO] [{self.loss_name}] kwargs: {kwargs}")
        experiment_type = kwargs.get('experiment_type', 'sim_vs_sim')

        # TODO: more loss types
        loss = defaultdict(dict)
        calculate_type = kwargs.get('calculate_type', ['rmse', 'mape'])
        calculate_cycles = kwargs.get('calculate_cycles', [1])
        for cycle in calculate_cycles:
            cycle_str = f"cycle_{cycle}"
            # get real voltage
            if experiment_type == 'sim_vs_sim':
                real_voltage = real_data[cycle_str]['voltage_in_V']
            elif experiment_type == 'real_vs_sim':
                real_voltage = real_data['formatted_cycle_data'][cycle_str][
                    'voltage_in_V']
            # get sim voltage
            sim_voltage = sim_data[cycle_str]['voltage_in_V']

            # interpolate voltage
            real_time = real_data[cycle_str]['time_in_s']
            sim_time = sim_data[cycle_str]['time_in_s']
            real_voltage = self.interpolate_curve(real_time, real_voltage, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')
            sim_voltage = self.interpolate_curve(sim_time, sim_voltage, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')

            # calculate loss
            if 'rmse' in calculate_type:
                loss[cycle_str]['rmse'] = self.calculate_rmse(
                    real_voltage, sim_voltage)
            if 'mape' in calculate_type:
                loss[cycle_str]['mape'] = self.calculate_mape(
                    real_voltage, sim_voltage)
        return loss

if __name__ == "__main__":
    loss = VoltageLoss()
    print(loss.calculate_loss(None, None))
    print(loss.loss_name)
