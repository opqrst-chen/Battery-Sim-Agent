from utils.base import ConfigManager
import numpy as np
from typing import List, Tuple
import pybamm

class CMAESConfigManager(ConfigManager):

    def __init__(self, config_dir: str = "configs"):
        super().__init__(config_dir=config_dir)

    def get_x_0(self) -> Tuple[List[float], List[str], List[float], List[float]]:
        x0 = []
        x0_upper_bounds = []
        x0_lower_bounds = []
        params_name = []
        default_params = self.get("pybamm.DEFAULT_PARAMS_SET")
        default_params_values = pybamm.ParameterValues(default_params)
        for param, bounds in self.get("cma_es.pbounds").items():
            # x0.append(np.random.uniform(bounds_min, bounds_max))
            x0.append(default_params_values[param])
            params_name.append(param)
            bounds_min = bounds["min"]
            bounds_max = bounds["max"]
            x0_lower_bounds.append(bounds_min)
            x0_upper_bounds.append(bounds_max)

        return x0, params_name, x0_lower_bounds, x0_upper_bounds