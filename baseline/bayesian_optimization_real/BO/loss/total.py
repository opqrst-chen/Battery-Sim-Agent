from typing import Dict, Any
import logging

from .base import BaseLoss

logger = logging.getLogger(__name__)

class TotalLoss(BaseLoss):

    def __init__(self):
        super().__init__("total")

    def calculate_loss(self, loss_list: Dict[str, Any], **kwargs) -> float:
        logger.info(f"[INFO] Calculating total loss...")
        print(f"[INFO] [{self.loss_name}] kwargs: {kwargs}")

        calculate_type = kwargs.get("calculate_type", "SUM").upper()
        calculate_cycles = kwargs.get('calculate_cycles', [1])

        total_loss = 0

        if calculate_type == "SUM":
            for cycle_idx in calculate_cycles:
                for loss_name in loss_list.keys():
                    total_loss += loss_list[loss_name].get(
                        "loss_value", {}).get(f"cycle_{cycle_idx}",
                                              {}).get('rmse', 0)

        return total_loss

if __name__ == "__main__":
    loss = TotalLoss()
    print(loss.calculate_loss(None, None))
    print(loss.loss_name)
