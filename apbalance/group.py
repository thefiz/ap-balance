from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Any
import random

from .runner import inspect_group


ASSUMPTION = (
    "Players are assumed to be capable of completing logically available checks "
    "as they become accessible, with comparable efficiency and without substantial "
    "skill, execution, routing, knowledge, break, or communication delays. Actual "
    "play time may differ significantly between games and players."
)


def _summarize(values: list[float | int]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "median": None,
            "mean": None,
            "max": None,
        }

    nums = [float(v) for v in values]
    avg = sum(nums) / len(nums)

    def clean(value: float):
        return int(value) if value.is_integer() else round(value, 3)

    return {
        "count": len(nums),
        "min": clean(min(nums)),
        "median": clean(float(median(nums))),
        "mean": clean(avg),
        "max": clean(max(nums)),
    }


def analyze_group(
    players_path: Path,
    archipelago_path: Path,
    *,
    apworld_paths: list[Path] | None = None,
    samples: int = 100,
    base_seed: int | None = None,
) -> dict[str, Any]:
    if samples < 1:
        raise ValueError("samples must be at least 1")

    rng = random.Random(base_seed)
    seeds = [rng.randrange(0, 2**31 - 1) for _ in range(samples)]

    results = [
        inspect_group(
            players_path=players_path,
            archipelago_path=archipelago_path,
            apworld_paths=apworld_paths,
            seed=seed,
        )
        for seed in seeds
    ]

    first = results[0]
    player_ids = [player["id"] for player in first["players"]]

    players_out: list[dict[str, Any]] = []

    for player_id in player_ids:
        identity = next(p for p in first["players"] if p["id"] == player_id)

        seed_rows = []
        for sample in results:
            player_result = sample["timeline_analysis"]["players"][str(player_id)]
            seed_rows.append({
                "seed": sample["seed"],
                **player_result,
            })

        pressure_events = [
            event
            for row in seed_rows
            for event in row["progression_pressure"]["events"]
        ]

        completion_positions = [
            row["early_completion"]["completion_position"]
            for row in seed_rows
            if row["early_completion"]["completion_position"] is not None
        ]
        peers_remaining = [
            row["early_completion"]["peers_still_active_fraction"]
            for row in seed_rows
            if row["early_completion"]["peers_still_active_fraction"] is not None
        ]
        idle_fractions = [
            row["idle"]["idle_fraction_before_completion"]
            for row in seed_rows
            if row["idle"]["idle_fraction_before_completion"] is not None
        ]

        players_out.append({
            "id": player_id,
            "name": identity["name"],
            "game": identity["game"],
            "samples": samples,
            "progression_pressure": {
                "seeds_with_pressure": sum(
                    1 for row in seed_rows
                    if row["progression_pressure"]["event_count"] > 0
                ),
                "seed_frequency": round(
                    sum(
                        1 for row in seed_rows
                        if row["progression_pressure"]["event_count"] > 0
                    ) / samples,
                    3,
                ),
                "events_per_seed": _summarize([
                    row["progression_pressure"]["event_count"]
                    for row in seed_rows
                ]),
                "checks_during_pressure_events": _summarize([
                    event["host_sendable_checks"]
                    for event in pressure_events
                ]),
                "waiting_players_per_event": _summarize([
                    event["waiting_player_count"]
                    for event in pressure_events
                ]),
                "external_progression_for_waiting_players_per_event": _summarize([
                    event["external_progression_for_waiting_players"]
                    for event in pressure_events
                ]),
            },
            "early_completion": {
                "completion_detection": sorted({
                    row["early_completion"]["completion_detection"]
                    for row in seed_rows
                }),
                "completion_position": _summarize(completion_positions),
                "peers_still_active_fraction_at_completion": _summarize(peers_remaining),
                "seeds_finishing_before_all_peers": sum(
                    1 for value in peers_remaining if value > 0
                ),
                "frequency_finishing_before_all_peers": (
                    round(sum(1 for value in peers_remaining if value > 0) / len(peers_remaining), 3)
                    if peers_remaining else None
                ),
            },
            "idle": {
                "seeds_with_idle": sum(
                    1 for row in seed_rows if row["idle"]["idle_step_count"] > 0
                ),
                "seed_frequency": round(
                    sum(1 for row in seed_rows if row["idle"]["idle_step_count"] > 0) / samples,
                    3,
                ),
                "idle_steps": _summarize([
                    row["idle"]["idle_step_count"]
                    for row in seed_rows
                ]),
                "idle_fraction_before_completion": _summarize(idle_fractions),
                "longest_idle_streak": _summarize([
                    row["idle"]["longest_idle_streak"]
                    for row in seed_rows
                ]),
            },
            "seed_results": seed_rows,
        })

    # Separate rankings for the three target failure modes. These are descriptive
    # rankings within the submitted group, not universal GOOD/BAD classifications.
    pressure_ranking = sorted(
        players_out,
        key=lambda p: (
            p["progression_pressure"]["seed_frequency"],
            p["progression_pressure"]["waiting_players_per_event"]["median"] or 0,
            p["progression_pressure"]["checks_during_pressure_events"]["median"] or 0,
        ),
        reverse=True,
    )

    early_ranking = sorted(
        players_out,
        key=lambda p: (
            p["early_completion"]["peers_still_active_fraction_at_completion"]["median"] or 0,
            -(p["early_completion"]["completion_position"]["median"] or 1),
        ),
        reverse=True,
    )

    idle_ranking = sorted(
        players_out,
        key=lambda p: (
            p["idle"]["idle_fraction_before_completion"]["median"] or 0,
            p["idle"]["longest_idle_streak"]["median"] or 0,
        ),
        reverse=True,
    )

    return {
        "schema_version": 1,
        "analyzer_version": "0.8.2",
        "mode": "group_multi_seed",
        "archipelago_version": first.get("archipelago_version"),
        "analysis_assumption": ASSUMPTION,
        "simulation": {
            "samples": samples,
            "base_seed": base_seed,
            "seeds": seeds,
        },
        "players": players_out,
        "rankings": {
            "progression_pressure": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "game": p["game"],
                    "seed_frequency": p["progression_pressure"]["seed_frequency"],
                    "median_waiting_players":
                        p["progression_pressure"]["waiting_players_per_event"]["median"],
                    "median_checks_during_pressure":
                        p["progression_pressure"]["checks_during_pressure_events"]["median"],
                }
                for p in pressure_ranking
            ],
            "early_completion": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "game": p["game"],
                    "median_completion_position":
                        p["early_completion"]["completion_position"]["median"],
                    "median_peers_still_active_fraction":
                        p["early_completion"]["peers_still_active_fraction_at_completion"]["median"],
                }
                for p in early_ranking
            ],
            "idle": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "game": p["game"],
                    "idle_seed_frequency": p["idle"]["seed_frequency"],
                    "median_idle_fraction_before_completion":
                        p["idle"]["idle_fraction_before_completion"]["median"],
                    "median_longest_idle_streak":
                        p["idle"]["longest_idle_streak"]["median"],
                }
                for p in idle_ranking
            ],
        },
        "samples": [
            {
                "seed": sample["seed"],
                "seed_name": sample["seed_name"],
                "timeline_analysis": sample["timeline_analysis"],
            }
            for sample in results
        ],
    }
