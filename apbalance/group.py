from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Any
import random

from .runner import inspect_group


ASSUMPTIONS = [
    (
        "Players are assumed to be capable of completing logically available "
        "checks as they become accessible, with comparable efficiency and without "
        "substantial skill, execution, routing, knowledge, break, or communication "
        "delays. Actual play time may differ significantly between games and players."
    ),
    (
        "Check starvation means that an unfinished player has no sendable "
        "Archipelago checks in the current logical progression step while another "
        "unfinished player does. It does not necessarily mean the player has no "
        "meaningful in-game activity."
    ),
    (
        "When a player completes their configured goal, all remaining items hosted "
        "in that player's world are assumed to be released immediately. Those "
        "post-goal locations no longer contribute player workload or bottleneck risk."
    ),
]


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

        dependency_events = [
            event
            for row in seed_rows
            for event in row["progression_bottleneck"]["dependency_events"]
        ]
        bottleneck_candidates = [
            event
            for row in seed_rows
            for event in row["progression_bottleneck"]["candidate_events"]
        ]
        candidate_workload_ratios = [
            event["workload_ratio_to_active_peer_median"]
            for event in bottleneck_candidates
            if event["workload_ratio_to_active_peer_median"] is not None
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
        starvation_fractions = [
            row["check_starvation"]["starvation_fraction_before_completion"]
            for row in seed_rows
            if row["check_starvation"]["starvation_fraction_before_completion"] is not None
        ]
        released_checks_min = [
            row["early_release"]["released_checks_min"] for row in seed_rows
        ]
        released_checks_expected = [
            row["early_release"]["released_checks_expected"] for row in seed_rows
        ]
        released_checks_max = [
            row["early_release"]["released_checks_max"] for row in seed_rows
        ]
        released_external_min = [
            row["early_release"]["released_external_progression_items_min"]
            for row in seed_rows
        ]
        released_external_expected = [
            row["early_release"]["released_external_progression_items_expected"]
            for row in seed_rows
        ]
        released_external_max = [
            row["early_release"]["released_external_progression_items_max"]
            for row in seed_rows
        ]
        release_recipients_min = [
            row["early_release"]["recipient_player_count_min"] for row in seed_rows
        ]
        release_recipients_max = [
            row["early_release"]["recipient_player_count_max"] for row in seed_rows
        ]
        release_ratios_expected = [
            row["early_release"]["release_checks_ratio_to_active_peer_median_expected"]
            for row in seed_rows
            if row["early_release"]["release_checks_ratio_to_active_peer_median_expected"] is not None
        ]
        early_release_indexes = [
            row["early_release"]["early_release_index"]
            for row in seed_rows
            if row["early_release"]["early_release_index"] is not None
        ]

        dependency_seed_count = sum(
            1 for row in seed_rows
            if row["progression_bottleneck"]["dependency_event_count"] > 0
        )
        bottleneck_candidate_seed_count = sum(
            1 for row in seed_rows
            if row["progression_bottleneck"]["candidate_event_count"] > 0
        )
        starvation_seed_count = sum(
            1 for row in seed_rows
            if row["check_starvation"]["starvation_step_count"] > 0
        )

        players_out.append({
            "id": player_id,
            "name": identity["name"],
            "game": identity["game"],
            "samples": samples,
            "progression_bottleneck": {
                "seeds_with_dependency_events": dependency_seed_count,
                "dependency_seed_frequency": round(dependency_seed_count / samples, 3),
                "seeds_with_bottleneck_candidates": bottleneck_candidate_seed_count,
                "bottleneck_candidate_seed_frequency": round(
                    bottleneck_candidate_seed_count / samples, 3
                ),
                "bottleneck_exposure_index": (
                    round(
                        (bottleneck_candidate_seed_count / samples)
                        * (
                            _summarize(candidate_workload_ratios)["median"]
                            if _summarize(candidate_workload_ratios)["median"] is not None
                            else 0
                        ),
                        3,
                    )
                ),
                "dependency_events_per_seed": _summarize([
                    row["progression_bottleneck"]["dependency_event_count"]
                    for row in seed_rows
                ]),
                "candidate_events_per_seed": _summarize([
                    row["progression_bottleneck"]["candidate_event_count"]
                    for row in seed_rows
                ]),
                "candidate_checks": _summarize([
                    event["host_sendable_checks"]
                    for event in bottleneck_candidates
                ]),
                "candidate_workload_ratio_to_active_peer_median":
                    _summarize(candidate_workload_ratios),
                "candidate_waiting_players": _summarize([
                    event["waiting_player_count"]
                    for event in bottleneck_candidates
                ]),
                "candidate_external_progression_for_waiting_players":
                    _summarize([
                        event["external_progression_for_waiting_players"]
                        for event in bottleneck_candidates
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
            "check_starvation": {
                "seeds_with_starvation": starvation_seed_count,
                "seed_frequency": round(starvation_seed_count / samples, 3),
                "starvation_steps": _summarize([
                    row["check_starvation"]["starvation_step_count"]
                    for row in seed_rows
                ]),
                "starvation_fraction_before_completion": _summarize(starvation_fractions),
                "longest_starvation_streak": _summarize([
                    row["check_starvation"]["longest_starvation_streak"]
                    for row in seed_rows
                ]),
            },
            "early_release": {
                "released_checks_min": _summarize(released_checks_min),
                "released_checks_expected": _summarize(released_checks_expected),
                "released_checks_max": _summarize(released_checks_max),
                "released_external_progression_items_min":
                    _summarize(released_external_min),
                "released_external_progression_items_expected":
                    _summarize(released_external_expected),
                "released_external_progression_items_max":
                    _summarize(released_external_max),
                "recipient_player_count_min": _summarize(release_recipients_min),
                "recipient_player_count_max": _summarize(release_recipients_max),
                "release_checks_ratio_to_active_peer_median_expected":
                    _summarize(release_ratios_expected),
                "early_release_index": _summarize(early_release_indexes),
            },
            "seed_results": seed_rows,
        })

    bottleneck_ranking = sorted(
        players_out,
        key=lambda p: (
            p["progression_bottleneck"]["bottleneck_exposure_index"],
            p["progression_bottleneck"]["bottleneck_candidate_seed_frequency"],
            p["progression_bottleneck"]["candidate_workload_ratio_to_active_peer_median"]["median"] or 0,
            p["progression_bottleneck"]["candidate_external_progression_for_waiting_players"]["median"] or 0,
            p["progression_bottleneck"]["candidate_waiting_players"]["median"] or 0,
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

    starvation_ranking = sorted(
        players_out,
        key=lambda p: (
            p["check_starvation"]["starvation_fraction_before_completion"]["median"] or 0,
            p["check_starvation"]["longest_starvation_streak"]["median"] or 0,
        ),
        reverse=True,
    )

    release_ranking = sorted(
        players_out,
        key=lambda p: (
            p["early_release"]["early_release_index"]["median"] or 0,
            p["early_release"]["released_external_progression_items_expected"]["median"] or 0,
            p["early_release"]["released_checks_expected"]["median"] or 0,
        ),
        reverse=True,
    )

    return {
        "schema_version": 2,
        "analyzer_version": "0.9.2",
        "mode": "group_multi_seed",
        "archipelago_version": first.get("archipelago_version"),
        "analysis_assumptions": ASSUMPTIONS,
        "simulation": {
            "samples": samples,
            "base_seed": base_seed,
            "seeds": seeds,
        },
        "players": players_out,
        "rankings": {
            "progression_bottleneck": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "game": p["game"],
                    "bottleneck_exposure_index":
                        p["progression_bottleneck"]["bottleneck_exposure_index"],
                    "bottleneck_candidate_seed_frequency":
                        p["progression_bottleneck"]["bottleneck_candidate_seed_frequency"],
                    "dependency_seed_frequency":
                        p["progression_bottleneck"]["dependency_seed_frequency"],
                    "median_candidate_workload_ratio_to_active_peer_median":
                        p["progression_bottleneck"]["candidate_workload_ratio_to_active_peer_median"]["median"],
                    "median_candidate_waiting_players":
                        p["progression_bottleneck"]["candidate_waiting_players"]["median"],
                    "median_candidate_external_progression":
                        p["progression_bottleneck"]["candidate_external_progression_for_waiting_players"]["median"],
                }
                for p in bottleneck_ranking
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
            "check_starvation": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "game": p["game"],
                    "starvation_seed_frequency":
                        p["check_starvation"]["seed_frequency"],
                    "median_starvation_fraction_before_completion":
                        p["check_starvation"]["starvation_fraction_before_completion"]["median"],
                    "median_longest_starvation_streak":
                        p["check_starvation"]["longest_starvation_streak"]["median"],
                }
                for p in starvation_ranking
            ],
            "early_release": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "game": p["game"],
                    "median_completion_position":
                        p["early_completion"]["completion_position"]["median"],
                    "median_peers_still_active_fraction":
                        p["early_completion"]["peers_still_active_fraction_at_completion"]["median"],
                    "median_released_checks_min":
                        p["early_release"]["released_checks_min"]["median"],
                    "median_released_checks_expected":
                        p["early_release"]["released_checks_expected"]["median"],
                    "median_released_checks_max":
                        p["early_release"]["released_checks_max"]["median"],
                    "median_released_external_progression_expected":
                        p["early_release"]["released_external_progression_items_expected"]["median"],
                    "median_release_checks_ratio_to_active_peer_median_expected":
                        p["early_release"]["release_checks_ratio_to_active_peer_median_expected"]["median"],
                    "median_early_release_index":
                        p["early_release"]["early_release_index"]["median"],
                }
                for p in release_ranking
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
