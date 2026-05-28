import os
import time
import shutil
import logging
import yaml
from typing import Dict, Any
import random
import numpy as np
import torch

class ConfigManager:
    """Simplified configuration manager for the Filter Framework"""

    def __init__(self, config_dir: str = "configs"):
        self.config_dir = config_dir
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not os.path.exists(self.config_dir):
            raise FileNotFoundError(
                f"Config file not found: {self.config_dir}")

        config = {}
        for file in os.listdir(self.config_dir):
            if file.endswith(".yaml"):
                with open(os.path.join(self.config_dir, file),
                          'r',
                          encoding='utf-8') as f:
                    config[file.split(".")[0]] = yaml.safe_load(f)
        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports nested keys with dot notation)"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    # TODO: implement the set method
    # def set(self, key: str, value: Any):
    #     """Set configuration value by key (supports nested keys with dot notation)"""
    #     keys = key.split('.')
    #     current = self.config
    #     for k in keys[:-1]:
    #         if k not in current:
    #             current[k] = {}
    #         current = current[k]
    #     current[keys[-1]] = value

    def get_all_configs(self) -> Dict[str, Any]:
        """Get all configurations"""
        return self.config

def init_experiment(results_dir: str = "./results/{time_stamp}",
                    code_dir: str = os.path.dirname(__file__),
                    SEED: int = 1234):
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    time_stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    RESULTS_DIR = results_dir.format(time_stamp=time_stamp)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(RESULTS_DIR, 'exp.log'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    code_backup_path = os.path.join(RESULTS_DIR, "code")
    shutil.copytree(src=code_dir,
                    dst=code_backup_path,
                    ignore=shutil.ignore_patterns('__pycache__'))
    logger.info(f"[Backup] Code backed up to: {code_backup_path}")
    config_backup_path = os.path.join(RESULTS_DIR, "configs")
    shutil.copytree(src="configs",
                    dst=config_backup_path,
                    ignore=shutil.ignore_patterns('__pycache__'))
    logger.info(f"[Backup] Configs backed up to: {config_backup_path}")

    return time_stamp, RESULTS_DIR

if __name__ == "__main__":
    time_stamp, RESULTS_DIR = init_experiment()
    print(time_stamp, RESULTS_DIR)
    config_manager = ConfigManager(config_dir="configs")
    print(config_manager.get("pybamm.SINGLE_CYCLE"))
