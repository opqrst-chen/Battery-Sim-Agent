from typing import Dict, Any
from abc import ABC
import numpy as np
from scipy.interpolate import PchipInterpolator
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

class BaseLoss(ABC):

    def __init__(self, loss_name: str):
        self.loss_name = loss_name

    def calculate_loss(self, real_data: Dict[str, Any],
                       sim_data: Dict[str, Any], **kwargs) -> float:
        raise NotImplementedError("subclasses must implement this method")

    def calculate_rmse(self, real_data, sim_data):
        """calculate rmse"""
        # Convert to numpy arrays
        real_data = np.asarray(real_data, dtype=float)
        sim_data = np.asarray(sim_data, dtype=float)

        # Pad shorter array with zeros
        max_len = max(len(real_data), len(sim_data))
        real_data = np.pad(real_data, (0, max_len - len(real_data)),
                           constant_values=np.nan)
        sim_data = np.pad(sim_data, (0, max_len - len(sim_data)),
                          constant_values=np.nan)

        # Replace NaN with 0
        real_data = np.nan_to_num(real_data, nan=0.0)
        sim_data = np.nan_to_num(sim_data, nan=0.0)
        # RMSE
        rmse_val = np.sqrt(np.mean((real_data - sim_data)**2))

        return rmse_val

    def calculate_mape(self, real_data, sim_data):
        """calculate mape"""
        # Convert to numpy arrays
        real_data = np.asarray(real_data, dtype=float)
        sim_data = np.asarray(sim_data, dtype=float)

        # Pad shorter array with zeros
        max_len = max(len(real_data), len(sim_data))
        real_data = np.pad(real_data, (0, max_len - len(real_data)),
                           constant_values=np.nan)
        sim_data = np.pad(sim_data, (0, max_len - len(sim_data)),
                          constant_values=np.nan)

        # Replace NaN with 0
        real_data = np.nan_to_num(real_data, nan=0.0)
        sim_data = np.nan_to_num(sim_data, nan=0.0)

        # MAPE (exclude division by zero)
        nonzero_mask = real_data != 0
        if np.any(nonzero_mask):
            mape_val = np.mean(
                np.abs((real_data[nonzero_mask] - sim_data[nonzero_mask]) /
                       real_data[nonzero_mask])) * 100
        else:
            mape_val = np.nan  # undefined if all real_data == 0

        return mape_val

    def interpolate_curve(self,
                          x,
                          y,
                          interpolate_num=None,
                          is_plot=False,
                          interpolate_method='PCHIP'):
        x = np.array(x)
        y = np.array(y)
        x = x - x[0]
        x, idx = np.unique(x, return_index=True)
        y = y[idx]

        if interpolate_num is None:
            interpolate_num = int(x.max())

        x_new = np.linspace(x.min(), x.max(), interpolate_num)

        if interpolate_method == 'PCHIP':
            f = PchipInterpolator(x, y)
            y_new = f(x_new)
        else:
            f = interp1d(x,
                         y,
                         kind="linear",
                         bounds_error=False,
                         fill_value="extrapolate")
            y_new = f(x_new)

        if is_plot:
            # plot
            plt.figure(figsize=(10, 8))

            plt.plot(x, y, label="Original")
            plt.plot(x_new, y_new, label=interpolate_method)
            # plt.plot(x_new, y_new1,label="Interpolated (Linear)")

            plt.xlabel("Time [s]")
            plt.ylabel("Voltage [V]")
            plt.legend()
            plt.show()
        return y_new

if __name__ == "__main__":
    loss = BaseLoss("capacity")
    print(loss.loss_name)
    print(loss.calculate_loss(None, None))
