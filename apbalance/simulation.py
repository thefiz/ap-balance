from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
import random

from .aggregate import aggregate_samples
from .configuration import describe_configuration
from .runner import inspect_yaml


def analyze_yaml(
    yaml_path: Path,
    archipelago_path: Path,
    *,
    apworld_path: Path | None = None,
    samples: int = 100,
    base_seed: int | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    if samples < 1:
        raise ValueError("samples must be at least 1")
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if apworld_path is not None and workers != 1:
        raise ValueError("custom .apworld simulation currently requires --workers 1")

    rng = random.Random(base_seed)
    seeds = [rng.randrange(0, 2**31 - 1) for _ in range(samples)]

    results: list[dict[str, Any] | None] = [None] * samples

    def run_one(index: int, seed: int):
        result = inspect_yaml(
            yaml_path=yaml_path,
            archipelago_path=archipelago_path,
            apworld_path=apworld_path,
            seed=seed,
        )
        return index, result

    if workers == 1:
        for i, seed in enumerate(seeds):
            _, result = run_one(i, seed)
            results[i] = result
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(run_one, i, seed)
                for i, seed in enumerate(seeds)
            ]
            for future in as_completed(futures):
                i, result = future.result()
                results[i] = result

    completed = [r for r in results if r is not None]
    if len(completed) != samples:
        raise RuntimeError("One or more simulation samples did not complete.")

    first = completed[0]
    configuration = describe_configuration(yaml_path)

    return {
        "schema_version": 1,
        "analyzer_version": "0.9.0",
        "mode": "multi_seed",
        "game": first["game"],
        "world_version": first.get("world_version"),
        "archipelago_version": first.get("archipelago_version"),
        "player": first["player"],
        "configuration": configuration,
        "simulation": {
            "samples": samples,
            "base_seed": base_seed,
            "workers": workers,
            "seeds": seeds,
        },
        "aggregate": aggregate_samples(completed),
        "samples": [
            {
                "seed": s["seed"],
                "seed_name": s["seed_name"],
                "world": s["world"],
                "logical_spheres": {
                    "count": s["logical_spheres"]["count"],
                    "unreachable_locations": s["logical_spheres"]["unreachable_locations"],
                },
                "analysis": s["analysis"],
            }
            for s in completed
        ],
    }
