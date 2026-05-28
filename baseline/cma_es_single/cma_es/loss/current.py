from collections import defaultdict
from typing import Dict, Any
import logging
import numpy as np

from .base import BaseLoss

logger = logging.getLogger(__name__)

class CurrentLoss(BaseLoss):

    def __init__(self):
        super().__init__("current")

    def calculate_loss(self, real_data: Dict[str, Any],
                       sim_data: Dict[str, Any], **kwargs) -> float:
        logger.info(f"[INFO] Calculating current loss...")
        print(f"[INFO] [{self.loss_name}] kwargs: {kwargs}")
        experiment_type = kwargs.get('experiment_type', 'sim_vs_sim')

        # TODO: more loss types

        loss = defaultdict(dict)
        calculate_type = kwargs.get('calculate_type', ['rmse', 'mape'])
        calculate_cycles = kwargs.get('calculate_cycles', [1])
        for cycle in calculate_cycles:
            cycle_str = f"cycle_{cycle}"
            # get real current
            if experiment_type == 'sim_vs_sim':
                real_current = real_data[cycle_str]['current_in_A']
            elif experiment_type == 'real_vs_sim':
                real_current = real_data['formatted_cycle_data'][cycle_str][
                    'current_in_A']
            # get sim current
            sim_current = sim_data[cycle_str]['current_in_A']
            
            # interpolate current
            real_time = real_data[cycle_str]['time_in_s']
            sim_time = sim_data[cycle_str]['time_in_s']
            real_current = self.interpolate_curve(real_time, real_current, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')
            sim_current = self.interpolate_curve(sim_time, sim_current, interpolate_num=None, is_plot=False, interpolate_method='PCHIP')

            # calculate loss
            if 'rmse' in calculate_type:
                loss[cycle_str]['rmse'] = self.calculate_rmse(
                    real_current, sim_current)
            if 'mape' in calculate_type:
                loss[cycle_str]['mape'] = self.calculate_mape(
                    real_current, sim_current)
        return loss

if __name__ == "__main__":
    loss = CurrentLoss()
    print(loss.calculate_loss(None, None))
    print(loss.loss_name)
