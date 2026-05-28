import argparse
import logging
import os
import shutil
import time

from utils.exp import get_configs
from pipeline.degradation_pipeline import degradation_pipeline
from pipeline.first_cycle_pipeline import first_cycle_pipeline

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline_name",
                        type=str,
                        default="first_cycle_pipeline")
    parser.add_argument("--multi_modal", type=bool, default=False)
    parser.add_argument("--test_id", type=int, default=None)
    parser.add_argument("--yaml_path", type=str, default="./generate_simulated_data/output/simulated_data_setting_single_new_filtered.yaml")
    return parser.parse_args()

import yaml
def read_yaml(yaml_file_path):
    with open(yaml_file_path, 'r') as yaml_file:
        data = yaml.safe_load(yaml_file)
    return data

def main():
    args = parse_args()
    print(args.yaml_path)
    # read yaml file and get specific settings
    settings = read_yaml(args.yaml_path)
    ori_settings = None
    if args.test_id and isinstance(args.test_id, int):
        ori_settings = settings[args.test_id]
        print(ori_settings)

    time_stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    RESULTS_DIR = get_configs(
        config_type="exp", config_name="RESULTS_DIR").format(id=args.test_id, time_stamp=time_stamp)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(RESULTS_DIR, 'exp.log'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    code_backup_path = os.path.join(RESULTS_DIR, "code")
    shutil.copytree(os.path.dirname(__file__),
                    code_backup_path,
                    ignore=shutil.ignore_patterns('__pycache__'))
    logger.info(f"[Backup] Code backed up to: {code_backup_path}")

    if args.pipeline_name == "degradation_pipeline":
        degradation_pipeline(RESULTS_DIR, time_stamp, ori_settings=ori_settings)

    
    elif args.pipeline_name == "first_cycle_pipeline":
        first_cycle_pipeline(RESULTS_DIR, time_stamp, multi_modal=args.multi_modal, ori_settings=ori_settings)

    else:
        raise ValueError(f"Invalid pipeline name: {args.pipeline_name}")

if __name__ == "__main__":
    main()

# python battery_agent/pipeline.py --pipeline_name first_cycle_pipeline --test_id 2
# python battery_agent/pipeline.py --pipeline_name first_cycle_pipeline --test_id 4  --yaml_path ./generate_simulated_data/output/simulated_data_setting_multi_new_filtered.yaml
# python battery_agent/pipeline.py --pipeline_name degradation_pipeline --test_id 1  --yaml_path ./generate_simulated_data/output/simulated_data_setting_SEI.yaml
