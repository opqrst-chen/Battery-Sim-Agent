#!/usr/bin/env python3
"""
Filter settings from a YAML file by uniformly sampling across groups, preserving original indices.

Usage examples:

  - Uniform by parameter key (default), keep ~20% from each parameter key group:
    python filter_settings.py \
      --input /share/project/cjw/test/BatteryAgent/generate_simulated_data/output/simulated_data_setting_single.yaml \
      --output /share/project/cjw/test/BatteryAgent/generate_simulated_data/output/simulated_data_setting_single.filtered.yaml \
      --ratio 0.2 \
      --group-by parameter_key \
      --seed 42

  - Uniform by parameter key and param_name composite, select exactly 200 total:
    python filter_settings.py \
      --num 200 \
      --group-by parameter_key+param_name

  - Evenly sample by index (every k-th):
    python filter_settings.py --num 500 --mode index

  - Keep a fixed number per param_name (balanced across c-rates and parameter keys):
    python filter_settings.py \
      --input /share/project/cjw/test/BatteryAgent/generate_simulated_data/output/simulated_data_setting_single.yaml \
      --mode per_param \
      --per-param-num 20

Notes:
  - The script preserves the original top-level YAML keys (indices) and their content exactly.
  - For modes 'group' and 'index', specify exactly one of --num or --ratio.
  - Default grouping is by the single key inside "parameter_change" (parameter_key).
"""

from __future__ import annotations

import argparse
import math
import random
from collections import defaultdict, OrderedDict
from typing import Dict, Iterable, List, Tuple, Any

import yaml

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Uniformly sample YAML settings while preserving indices")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input YAML mapping of index -> setting",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=
        "Path to write filtered YAML. If omitted and --inplace is not set, appends .filtered.yaml",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite the input YAML in place",
    )
    size_group = parser.add_mutually_exclusive_group(required=False)
    size_group.add_argument(
        "--num",
        type=int,
        help="Total number of settings to keep",
    )
    size_group.add_argument(
        "--ratio",
        type=float,
        help="Fraction (0-1] of settings to keep",
    )
    parser.add_argument(
        "--mode",
        choices=["group", "index", "per_param"],
        default="group",
        help=
        "Sampling mode: 'group' for uniform per group, 'index' for evenly spaced by index, 'per_param' to keep a fixed number per param_name",
    )
    parser.add_argument(
        "--group-by",
        choices=[
            "parameter_key",
            "param_name",
            "charge_c_rate",
            "discharge_c_rate",
            "model_name",
            "parameter_key+param_name",
        ],
        default="parameter_key",
        help="Grouping field used when --mode=group",
    )
    parser.add_argument(
        "--per-param-num",
        type=int,
        default=20,
        help=
        "When --mode=per_param, number of settings to keep for each param_name (default: 20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for reproducibility",
    )
    return parser.parse_args()

def load_yaml_mapping(path: str) -> Dict[int, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Input YAML must be a mapping of index -> setting")
    # Coerce keys to int if possible to make ordering deterministic
    normalized: Dict[int, Any] = {}
    for key, value in data.items():
        try:
            idx = int(key)
        except (TypeError, ValueError):
            # Keep as-is if non-numeric key
            idx = key  # type: ignore[assignment]
        normalized[idx] = value
    return normalized

def extract_parameter_key(setting: Dict[str, Any]) -> str:
    parameter_change = setting.get("parameter_change", {}) or {}
    if not isinstance(parameter_change, dict):
        return "__none__"
    if len(parameter_change) == 0:
        return "__none__"
    # Expect exactly one changed parameter; if multiple, join their names
    keys = list(parameter_change.keys())
    if len(keys) == 1:
        return str(keys[0])
    return "+".join(str(k) for k in sorted(keys))

def make_group_key(setting: Dict[str, Any], strategy: str) -> str:
    if strategy == "parameter_key":
        return extract_parameter_key(setting)
    if strategy == "param_name":
        return str(setting.get("param_name"))
    if strategy == "charge_c_rate":
        return str(setting.get("charge_c_rate"))
    if strategy == "discharge_c_rate":
        return str(setting.get("discharge_c_rate"))
    if strategy == "model_name":
        return str(setting.get("model_name"))
    if strategy == "parameter_key+param_name":
        return f"{extract_parameter_key(setting)}|{setting.get('param_name')}"
    raise ValueError(f"Unsupported group-by strategy: {strategy}")

def extract_param_value(setting: Dict[str, Any]) -> Tuple[bool, float]:
    parameter_change = setting.get("parameter_change", {}) or {}
    if not isinstance(parameter_change, dict) or len(parameter_change) == 0:
        return False, 0.0
    # Use the first key's value (expect single-key changes)
    key = next(iter(sorted(parameter_change.keys())))
    value = parameter_change[key]
    if isinstance(value, (int, float)):
        return True, float(value)
    try:
        return True, float(str(value))
    except Exception:
        return False, 0.0

def compute_target_counts_per_group(
    group_to_indices: Dict[str, List[int]],
    total_to_keep: int,
) -> Dict[str, int]:
    num_groups = len(group_to_indices)
    if num_groups == 0:
        return {}
    base = total_to_keep // num_groups
    remainder = total_to_keep % num_groups

    # Start with base allocation, then distribute remainder to the largest groups first
    # but do not exceed available items in each group.
    targets = {g: min(base, len(idxs)) for g, idxs in group_to_indices.items()}

    # Compute a priority list: groups with more available headroom get remainder first
    # headroom = available - allocated
    groups_by_headroom = sorted(
        group_to_indices.keys(),
        key=lambda g:
        (len(group_to_indices[g]) - targets[g], len(group_to_indices[g])),
        reverse=True,
    )
    for g in groups_by_headroom:
        if remainder <= 0:
            break
        if targets[g] < len(group_to_indices[g]):
            targets[g] += 1
            remainder -= 1

    # If some groups still exceed availability due to small groups, redistribute
    if remainder > 0:
        # Fill remaining quota from any groups that still have availability
        for g in groups_by_headroom:
            if remainder <= 0:
                break
            available = len(group_to_indices[g]) - targets[g]
            if available <= 0:
                continue
            take = min(available, remainder)
            targets[g] += take
            remainder -= take

    return targets

def uniform_group_sample(
    index_to_setting: Dict[int, Dict[str, Any]],
    total_to_keep: int,
    group_by: str,
    seed: int,
) -> List[int]:
    random.seed(seed)
    # Partition indices by group
    group_to_indices: Dict[str, List[int]] = defaultdict(list)
    for idx, setting in index_to_setting.items():
        group_key = make_group_key(setting, group_by)
        group_to_indices[group_key].append(idx)

    # Shuffle within each group for randomness
    for idxs in group_to_indices.values():
        random.shuffle(idxs)

    targets = compute_target_counts_per_group(group_to_indices, total_to_keep)

    selected: List[int] = []
    # Fair round-robin picking to reduce bias
    # Prepare iterators for each group
    group_iters: List[Tuple[str, Iterable[int]]] = []
    for g, idxs in group_to_indices.items():
        group_iters.append((g, iter(idxs)))

    # Keep counters
    picked_per_group = {g: 0 for g in group_to_indices}
    remaining_per_group = dict(targets)

    # Continue while any group still needs items
    # Iterate cyclically over groups
    while any(remaining > 0 for remaining in remaining_per_group.values()):
        for g, it in group_iters:
            if remaining_per_group.get(g, 0) <= 0:
                continue
            try:
                next_idx = next(it)
            except StopIteration:
                remaining_per_group[g] = 0
                continue
            selected.append(next_idx)
            picked_per_group[g] += 1
            remaining_per_group[g] -= 1
            if sum(picked_per_group.values()) >= total_to_keep:
                break
        if len(selected) >= total_to_keep:
            break

    # If due to small groups we still have quota, fill from any remaining indices
    if len(selected) < total_to_keep:
        leftover = [
            idx for g, idxs in group_to_indices.items() for idx in idxs
            if idx not in selected
        ]
        random.shuffle(leftover)
        needed = total_to_keep - len(selected)
        selected.extend(leftover[:needed])

    return selected

def evenly_select_positions(num_items: int, quota: int) -> List[int]:
    if quota >= num_items:
        return list(range(num_items))
    if quota <= 0 or num_items <= 0:
        return []
    step = num_items / float(quota)
    positions: List[int] = []
    for i in range(quota):
        pos = int(math.floor((i + 0.5) * step))
        if pos >= num_items:
            pos = num_items - 1
        positions.append(pos)
    # Deduplicate while preserving order
    seen = set()
    unique_positions: List[int] = []
    for p in positions:
        if p not in seen:
            unique_positions.append(p)
            seen.add(p)
    if len(unique_positions) < quota:
        for j in range(num_items):
            if j not in seen:
                unique_positions.append(j)
                seen.add(j)
                if len(unique_positions) == quota:
                    break
    return unique_positions

def sample_per_param_name(
    index_to_setting: Dict[int, Dict[str, Any]],
    per_param_num: int,
    seed: int,
) -> List[int]:
    # Group by param_name
    param_to_indices: Dict[str, List[int]] = defaultdict(list)
    for idx, setting in index_to_setting.items():
        param_to_indices[str(setting.get("param_name"))].append(idx)

    selected: List[int] = []

    # Global order map for stable ordering
    order_map_global = {
        idx: order
        for order, idx in enumerate(index_to_setting.keys())
    }

    for param_name, param_indices in param_to_indices.items():
        # Partition by c-rate pair
        pair_to_indices: Dict[str, List[int]] = defaultdict(list)
        for idx in param_indices:
            s = index_to_setting[idx]
            pair_key = f"{s.get('charge_c_rate')}|{s.get('discharge_c_rate')}"
            pair_to_indices[pair_key].append(idx)

        # Allocate per pair
        pair_targets = compute_target_counts_per_group(pair_to_indices,
                                                       per_param_num)

        chosen_for_param: List[int] = []
        for pair_key in sorted(pair_to_indices.keys()):
            cpair_indices = pair_to_indices[pair_key]
            t_for_pair = pair_targets.get(pair_key, 0)
            if t_for_pair <= 0:
                continue

            # Within pair, partition by parameter key
            key_to_indices: Dict[str, List[int]] = defaultdict(list)
            for idx in cpair_indices:
                key_to_indices[extract_parameter_key(
                    index_to_setting[idx])].append(idx)

            key_targets = compute_target_counts_per_group(
                key_to_indices, t_for_pair)

            for pkey in sorted(key_to_indices.keys()):
                group_indices = key_to_indices[pkey]
                t = key_targets.get(pkey, 0)
                if t <= 0:
                    continue

                # Order by parameter numeric value if possible for representativeness
                numeric: List[Tuple[float, int]] = []
                non_numeric: List[int] = []
                for idx in group_indices:
                    ok, val = extract_param_value(index_to_setting[idx])
                    if ok:
                        numeric.append((val, idx))
                    else:
                        non_numeric.append(idx)
                ordered_indices: List[int]
                if numeric:
                    numeric.sort(key=lambda x: x[0])
                    ordered_indices = [i for _, i in numeric] + non_numeric
                else:
                    ordered_indices = sorted(
                        group_indices,
                        key=lambda i: order_map_global.get(i, i))

                positions = evenly_select_positions(len(ordered_indices), t)
                chosen_for_param.extend(ordered_indices[p] for p in positions)

        # Top up if under quota
        if len(chosen_for_param) < per_param_num:
            remaining = [
                i for i in param_indices if i not in set(chosen_for_param)
            ]
            remaining_sorted = sorted(remaining,
                                      key=lambda i: order_map_global.get(i, i))
            positions = evenly_select_positions(
                len(remaining_sorted), per_param_num - len(chosen_for_param))
            chosen_for_param.extend(remaining_sorted[p] for p in positions)

        # Cap and stabilize order
        chosen_for_param = list(
            OrderedDict.fromkeys(chosen_for_param))[:per_param_num]
        chosen_for_param.sort(key=lambda i: order_map_global.get(i, i))
        selected.extend(chosen_for_param)

    return selected

def evenly_sample_by_index(indices: List[int],
                           total_to_keep: int) -> List[int]:
    if total_to_keep >= len(indices):
        return indices
    # Evenly spaced selection across sorted indices
    indices_sorted = sorted(indices)
    step = len(indices_sorted) / float(total_to_keep)
    chosen: List[int] = []
    pos = 0.0
    for _ in range(total_to_keep):
        chosen.append(indices_sorted[math.floor(pos)])
        pos += step
    # Ensure uniqueness and preserve original order
    chosen_unique = list(OrderedDict.fromkeys(chosen).keys())
    # If duplicates reduced count, top up with remaining nearest indices
    if len(chosen_unique) < total_to_keep:
        remaining = [i for i in indices_sorted if i not in chosen_unique]
        chosen_unique.extend(remaining[:total_to_keep - len(chosen_unique)])
    return chosen_unique

def write_yaml_mapping(path: str, index_to_setting: Dict[int, Any],
                       selected_indices: List[int]) -> None:
    # Preserve original order of selected indices as they appeared in the file
    # Fall back to sorted order if order cannot be inferred.
    order_map = {
        idx: order
        for order, idx in enumerate(index_to_setting.keys())
    }
    selected_sorted = sorted(selected_indices,
                             key=lambda i: order_map.get(i, i))

    # Use plain dict to ensure PyYAML can represent it; Python 3.7+ preserves insertion order
    output_mapping: Dict[Any, Any] = {}
    for idx in selected_sorted:
        output_mapping[idx] = index_to_setting[idx]

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(output_mapping, f, sort_keys=False, allow_unicode=True)

def main() -> None:
    args = parse_args()

    index_to_setting = load_yaml_mapping(args.input)
    total_count = len(index_to_setting)

    if args.mode == "per_param":
        if args.per_param_num <= 0:
            raise ValueError("--per-param-num must be positive")
        selected_indices = sample_per_param_name(
            index_to_setting=index_to_setting,
            per_param_num=args.per_param_num,
            seed=args.seed,
        )
    else:
        # Modes requiring global target size
        if args.ratio is not None:
            if not (0.0 < args.ratio <= 1.0):
                raise ValueError("--ratio must be in (0, 1]")
            total_to_keep = max(1, int(round(total_count * args.ratio)))
        elif args.num is not None:
            if args.num <= 0:
                raise ValueError("--num must be positive")
            total_to_keep = min(args.num, total_count)
        else:
            raise ValueError(
                "For modes 'group' and 'index', specify one of --num or --ratio"
            )

        if args.mode == "group":
            selected_indices = uniform_group_sample(
                index_to_setting=index_to_setting,
                total_to_keep=total_to_keep,
                group_by=args.group_by,
                seed=args.seed,
            )
        elif args.mode == "index":
            selected_indices = evenly_sample_by_index(
                list(index_to_setting.keys()), total_to_keep)
        else:
            raise ValueError(f"Unsupported mode: {args.mode}")

    output_path = args.output
    if args.inplace:
        output_path = args.input
    elif not output_path:
        output_path = args.input.rsplit(".", 1)[0] + "_filtered.yaml"

    write_yaml_mapping(output_path, index_to_setting, selected_indices)

    print(
        f"Selected {len(selected_indices)} of {total_count} settings. Saved to: {output_path}"
    )

if __name__ == "__main__":
    main()

"""
python generate_simulated_data/filter_settings.py --input generate_simulated_data/output/simulated_data_setting_multi_new.yaml --mode per_param --per-param-num 20 --seed 42
"""