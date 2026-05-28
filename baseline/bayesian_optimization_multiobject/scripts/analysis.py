#!/usr/bin/env python3
import os
import re
import json
import yaml

RESULTS_DIR = "results"
OUTPUT_FILE = os.path.join(RESULTS_DIR, "analysis.jsonl")

def extract_best_param_value(log_path):
    if not os.path.exists(log_path):
        return None
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if "[INFO] Best parameters:" in line:
                match = re.search(r"([-+]?\d*\.\d+|\d+)", line)
                if match:
                    return float(match.group(1))
    return None

def read_exp_index(yaml_path):
    if not os.path.exists(yaml_path):
        return None
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data.get("EXP_INDEX")

def find_matching_record(jsonl_path, target_value):
    if not os.path.exists(jsonl_path):
        return None
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
                if contains_value(record, target_value):
                    return record
            except json.JSONDecodeError:
                continue
    return None

def contains_value(obj, target_value, tol=1e-9):
    if isinstance(obj, dict):
        return any(contains_value(v, target_value, tol) for v in obj.values())
    elif isinstance(obj, list):
        return any(contains_value(v, target_value, tol) for v in obj)
    elif isinstance(obj, (int, float)):
        return abs(obj - target_value) < tol
    return False

def main():
    matched_count = 0
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for root, dirs, files in os.walk(RESULTS_DIR):
            if "exp.log" in files and "bo_records.jsonl" in files:
                log_path = os.path.join(root, "exp.log")
                bo_path = os.path.join(root, "bo_records.jsonl")
                yaml_path = os.path.join(root, "configs", "pybamm.yaml")

                best_value = extract_best_param_value(log_path)
                print(f"[DEBUG] best_value: {best_value}")
                if best_value is None:
                    continue

                record = find_matching_record(bo_path, best_value)
                if record is None:
                    continue

                exp_index = read_exp_index(yaml_path)
                if exp_index is None:
                    continue

                out_f.write(
                    json.dumps({exp_index: record}, ensure_ascii=False) + "\n")
                matched_count += 1

    print(f"analysis complete: matched {matched_count} rows, saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
