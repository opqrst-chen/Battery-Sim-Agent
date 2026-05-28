from .total import TotalLoss
from .capacity import CapacityLoss
from .voltage import VoltageLoss
from .current import CurrentLoss

class LossFactory:

    @staticmethod
    def get_loss(loss_name: str):
        if loss_name == "total":
            return TotalLoss()
        if loss_name == "capacity":
            return CapacityLoss()
        if loss_name == "voltage":
            return VoltageLoss()
        if loss_name == "current":
            return CurrentLoss()
