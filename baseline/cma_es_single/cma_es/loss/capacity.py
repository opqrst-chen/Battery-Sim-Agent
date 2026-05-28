from collections import defaultdict
from typing import Dict, Any
import logging

from .base import BaseLoss

logger = logging.getLogger(__name__)

class CapacityLoss(BaseLoss):

    def __init__(self):
        super().__init__("capacity")

    def calculate_loss(self, real_data: Dict[str, Any],
                       sim_data: Dict[str, Any], **kwargs) -> float:
        logger.info(f"[INFO] Calculating capacity loss...")
        print(f"[INFO] [{self.loss_name}] kwargs: {kwargs}")
        experiment_type = kwargs.get('experiment_type', 'sim_vs_sim')

        loss = defaultdict(dict)
        calculate_type = kwargs.get('calculate_type', ['rmse', 'mape'])
        calculate_cycles = kwargs.get('calculate_cycles', [1])
        for cycle in calculate_cycles:
            cycle_str = f"cycle_{cycle}"
            # get real capacity
            if experiment_type == 'sim_vs_sim':
                real_capacity = real_data[cycle_str]['capacity_in_Ah']
            elif experiment_type == 'real_vs_sim':
                real_capacity = real_data['formatted_cycle_data'][cycle_str][
                    'capacity_in_Ah']
            # get sim capacity
            sim_capacity = sim_data[cycle_str]['capacity_in_Ah']
            # calculate loss
            if 'rmse' in calculate_type:
                loss[cycle_str]['rmse'] = self.calculate_rmse(
                    [real_capacity], [sim_capacity])
            if 'mape' in calculate_type:
                loss[cycle_str]['mape'] = self.calculate_mape(
                    [real_capacity], [sim_capacity])
        print(f"[INFO] capacity loss: {loss}")
        return loss

if __name__ == "__main__":
    loss = CapacityLoss()
    real_data = {'cycle_1': {'capacity_in_Ah': [1.0, 0.9, 0.8]}}
    sim_data = {'cycle_1': {'capacity_in_Ah': [1.0, 0.85, 0.75]}}
    result = loss.calculate_loss(real_data,
                                 sim_data,
                                 experiment_type='sim_vs_sim',
                                 calculate_type=['rmse', 'mape'],
                                 calculate_cycles=[1])
    print(result)
    print(loss.loss_name)
