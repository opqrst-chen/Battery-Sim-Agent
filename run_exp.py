# run_jobs.py
import argparse
import sys
import yaml
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
import subprocess

def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def run_one(key: str, worker: str, python_exec: str, yaml_path:str,  extra_args: list[str]) -> tuple[str, int, str, str]:
    """
    Run worker.py as a separate process for a single key.
    Returns (key, returncode, stdout, stderr)
    """
    # print(extra_args)
    cmd = [python_exec, worker, "--test_id", str(key), "--yaml_path", yaml_path, *extra_args]
    # Capture output for logging/inspection
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return key, proc.returncode, proc.stdout, proc.stderr

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to YAML file")
    parser.add_argument("--worker", default="worker.py", help="Python file to call for each key")
    parser.add_argument("--max-proc", type=int, default=0, help="Max parallel processes (0 = CPU count)")
    # Any extra args after '--' will be forwarded to the worker
    parser.add_argument("remainder", nargs=argparse.REMAINDER, help="Use '--' then extra args for worker")
    args = parser.parse_args()

    cfg = load_yaml(args.config)
    if not isinstance(cfg, dict):
        print("YAML root must be a mapping (dict).", file=sys.stderr)
        sys.exit(2)

    keys = list(cfg.keys())
    if not keys:
        print("No top-level keys found in YAML.", file=sys.stderr)
        sys.exit(0)
    
    print(keys)
    # keys = keys[80:]
    # print(keys)
    # Determine Python executable (more portable than hardcoding 'python')
    python_exec = sys.executable or "python"
    max_workers = args.max_proc or (os.cpu_count() or 1)

    print(f"Discovered {len(keys)} keys. Running up to {max_workers} in parallel...\n")

    # Forward everything after a leading '--' to worker (optional)
    extra_args = []
    if args.remainder and args.remainder[0] == "--":
        extra_args = args.remainder[1:]
    # extra_args = f"yaml_path={args.config}"

    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(run_one, key, args.worker, python_exec, args.config,  extra_args): key
            for key in keys
        }
        for fut in as_completed(futures):
            key, code, out, err = fut.result()
            results.append((key, code, out, err))
            status = "OK" if code == 0 else f"FAIL({code})"
            print(f"[{status}] key={key}")
            if out.strip():
                print(f"  stdout:\n{indent(out)}")
            if err.strip():
                print(f"  stderr:\n{indent(err)}")

    # Optionally, make the overall exit code fail if any worker failed
    any_fail = any(code != 0 for _, code, _, _ in results)
    sys.exit(1 if any_fail else 0)

def indent(s: str, prefix: str = "    ") -> str:
    return "".join(prefix + line for line in s.splitlines(True))

if __name__ == "__main__":
    main()

# Examples:
# python run_exp.py --config ./generate_simulated_data/output/simulated_data_setting_single_new_filtered.yaml --worker ./battery_agent/pipeline.py --max-proc 4
# python run_exp.py --config ./generate_simulated_data/output/simulated_data_setting_multi_new_filtered.yaml  --worker ./battery_agent/pipeline.py --max-proc 4