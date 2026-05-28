#!/usr/bin/env python3
import os
import yaml
import argparse

RESULTS_DIR = "results"
TOTAL_EXP_INDEX = set(range(1, 891))  # 1~890

def count_jsonl_lines(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return None

def read_exp_index(yaml_path):
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("EXP_INDEX")
    except FileNotFoundError:
        return None
    except yaml.YAMLError as e:
        print(f"YAML parse error: {yaml_path} - {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="check experiments missing from results or with fewer than 20 entries")
    parser.add_argument("--missing-only",
                        action="store_true",
                        help="print only missing EXP_INDEX values, space separated")
    args = parser.parse_args()

    found_exp_indexes = set()

    if not args.missing_only:
        print("=== experiments with fewer than 20 entries ===")

    for root, dirs, files in os.walk(RESULTS_DIR):
        if "bo_records.jsonl" in files:
            bo_path = os.path.join(root, "bo_records.jsonl")
            line_count = count_jsonl_lines(bo_path)

            configs_dir = os.path.join(root, "configs")
            yaml_path = os.path.join(configs_dir, "pybamm.yaml")
            exp_index = read_exp_index(yaml_path)

            if exp_index is not None:
                found_exp_indexes.add(exp_index)

            if not args.missing_only and line_count is not None and line_count < 20:
                print(
                    f"[<20 entries] {bo_path} -> lines: {line_count}, EXP_INDEX: {exp_index}"
                )

    missing_exp_indexes = sorted(TOTAL_EXP_INDEX - found_exp_indexes)

    if args.missing_only:
        print(" ".join(map(str, missing_exp_indexes)))
    else:
        print("\n=== missing EXP_INDEX ===")
        print(missing_exp_indexes)
        print(f"total missing: {len(missing_exp_indexes)}")

if __name__ == "__main__":
    main()
