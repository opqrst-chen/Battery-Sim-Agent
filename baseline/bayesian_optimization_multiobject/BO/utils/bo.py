from utils.base import ConfigManager

from ax.api.configs import RangeParameterConfig

class BOConfigManager(ConfigManager):

    def __init__(self, config_dir: str = "configs"):
        super().__init__(config_dir=config_dir)

    def get_pbounds_range(self):
        pbounds_range = {}
        for param, bounds in self.get("BO.pbounds").items():
            pbounds_range[param] = (bounds["min"], bounds["max"])

        # TODO: use the set method to save the pbounds_range
        # self.set("BO.pbounds_range", pbounds_range)

        return pbounds_range

def pbounds_to_ax_parameters(pbounds, scale_factor=1e10):
    converted_bounds = []
    name_mapping = {}

    for name, (lower, upper) in pbounds.items():
        cleaned_name = (name.replace(" ", "_").replace("[", "").replace(
            "]", "").replace("(", "").replace(")", ""))

        name_mapping[cleaned_name] = name

        if lower <= 0:
            lower = 1e-20
        if upper <= 0:
            upper = 1e-20

        scaled_low = lower * scale_factor
        scaled_high = upper * scale_factor

        if scaled_high < scaled_low:
            raise ValueError(
                f"Upper bound {scaled_high} must be greater than lower bound {scaled_low}."
            )
        if scaled_high - scaled_low < 1e-15:
            raise ValueError(
                f"Parameter range ({scaled_high - scaled_low}) is too small. Consider reparameterizing."
            )

        param = RangeParameterConfig(
            name=cleaned_name,
            parameter_type="float",   
            bounds=(scaled_low, scaled_high),  
            scaling="log"
        )
        converted_bounds.append(param)

    return converted_bounds, name_mapping
