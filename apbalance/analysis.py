from __future__ import annotations

from statistics import mean, median
from typing import Any


DEFAULT_THIN_SPHERE_MAX = 3
DEFAULT_WIDE_SPHERE_MIN = 30
EARLY_SPHERE_COUNT = 5


def _sphere_widths(spheres: list[dict[str, Any]]) -> list[int]:
    return [int(sphere["checks"]) for sphere in spheres]


def _progression_counts(spheres: list[dict[str, Any]]) -> list[int]:
    return [int(sphere["progression_items"]) for sphere in spheres]


def _sendable_progression_counts(spheres: list[dict[str, Any]]) -> list[int]:
    return [
        sum(
            1
            for location in sphere.get("locations", [])
            if location.get("progression") and location.get("sendable")
        )
        for sphere in spheres
    ]


def _cumulative(values: list[int]) -> list[int]:
    total = 0
    result = []
    for value in values:
        total += value
        result.append(total)
    return result


def _consecutive_runs(indices: list[int]) -> list[list[int]]:
    if not indices:
        return []

    runs: list[list[int]] = [[indices[0]]]
    for index in indices[1:]:
        if index == runs[-1][-1] + 1:
            runs[-1].append(index)
        else:
            runs.append([index])
    return runs


def analyze_single_seed(
    spheres: list[dict[str, Any]],
    *,
    thin_sphere_max: int = DEFAULT_THIN_SPHERE_MAX,
    wide_sphere_min: int = DEFAULT_WIDE_SPHERE_MIN,
    early_sphere_count: int = EARLY_SPHERE_COUNT,
) -> dict[str, Any]:
    widths = _sphere_widths(spheres)
    progression = _progression_counts(spheres)
    sendable_progression = _sendable_progression_counts(spheres)
    cumulative_checks = _cumulative(widths)

    if not widths:
        return {
            "sphere_width": {},
            "early_workload": {},
            "thin_spheres": {},
            "wide_spheres": {},
            "progression_dilution": {},
        }

    terminal_index = len(widths) - 1

    all_thin = [
        {
            "index": index,
            "checks": width,
            "progression_items": progression[index],
            "sendable_progression_items": sendable_progression[index],
            "terminal": index == terminal_index,
        }
        for index, width in enumerate(widths)
        if width <= thin_sphere_max
    ]

    mid_thin = [entry for entry in all_thin if not entry["terminal"]]
    mid_thin_indices = [entry["index"] for entry in mid_thin]
    thin_runs = _consecutive_runs(mid_thin_indices)

    all_wide = [
        {
            "index": index,
            "checks": width,
            "progression_items": progression[index],
            "sendable_progression_items": sendable_progression[index],
            "opening": index == 0,
            "early": index < early_sphere_count,
        }
        for index, width in enumerate(widths)
        if width >= wide_sphere_min
    ]

    post_opening_wide = [entry for entry in all_wide if not entry["opening"]]
    early_post_opening_wide = [
        entry for entry in post_opening_wide if entry["early"]
    ]

    dilution = []
    sendable_dilution = []
    for index, (width, prog, sendable_prog) in enumerate(
        zip(widths, progression, sendable_progression)
    ):
        dilution.append({
            "index": index,
            "checks": width,
            "progression_items": prog,
            "checks_per_progression_item": (
                round(width / prog, 3) if prog > 0 else None
            ),
        })
        sendable_dilution.append({
            "index": index,
            "checks": width,
            "sendable_progression_items": sendable_prog,
            "checks_per_sendable_progression_item": (
                round(width / sendable_prog, 3) if sendable_prog > 0 else None
            ),
        })

    early_limit = min(early_sphere_count, len(widths))
    early_growth = []
    for index in range(1, early_limit):
        previous = cumulative_checks[index - 1]
        current = cumulative_checks[index]
        early_growth.append({
            "index": index,
            "sphere_checks": widths[index],
            "cumulative_checks": current,
            "growth_from_previous_cumulative": current - previous,
        })

    early = {
        "sphere_count_considered": early_limit,
        "checks_by_sphere": [
            {
                "index": index,
                "sphere_checks": widths[index],
                "cumulative_checks": cumulative_checks[index],
            }
            for index in range(early_limit)
        ],
        "growth_after_opening": early_growth,
        "checks_through_sphere_0": cumulative_checks[0],
        "checks_through_sphere_1": (
            cumulative_checks[1] if len(cumulative_checks) > 1 else cumulative_checks[-1]
        ),
        "checks_through_sphere_2": (
            cumulative_checks[2] if len(cumulative_checks) > 2 else cumulative_checks[-1]
        ),
        "checks_through_sphere_4": (
            cumulative_checks[4] if len(cumulative_checks) > 4 else cumulative_checks[-1]
        ),
    }

    ratios = [
        entry["checks_per_progression_item"]
        for entry in dilution
        if entry["checks_per_progression_item"] is not None
    ]
    sendable_ratios = [
        entry["checks_per_sendable_progression_item"]
        for entry in sendable_dilution
        if entry["checks_per_sendable_progression_item"] is not None
    ]

    return {
        "sphere_width": {
            "count": len(widths),
            "min": min(widths),
            "max": max(widths),
            "mean": round(mean(widths), 3),
            "median": median(widths),
            "largest_sphere_index": widths.index(max(widths)),
            "smallest_sphere_index": widths.index(min(widths)),
        },
        "early_workload": early,
        "thin_spheres": {
            "threshold_max_checks": thin_sphere_max,
            "all_count": len(all_thin),
            "mid_progression_count": len(mid_thin),
            "terminal_count": sum(1 for entry in all_thin if entry["terminal"]),
            "mid_progression_spheres": mid_thin,
            "terminal_spheres": [entry for entry in all_thin if entry["terminal"]],
            "consecutive_runs": [
                {
                    "start": run[0],
                    "end": run[-1],
                    "length": len(run),
                    "indices": run,
                }
                for run in thin_runs
            ],
            "longest_consecutive_run": max((len(run) for run in thin_runs), default=0),
        },
        "wide_spheres": {
            "threshold_min_checks": wide_sphere_min,
            "all_count": len(all_wide),
            "opening_count": sum(1 for entry in all_wide if entry["opening"]),
            "post_opening_count": len(post_opening_wide),
            "early_post_opening_count": len(early_post_opening_wide),
            "opening_spheres": [entry for entry in all_wide if entry["opening"]],
            "post_opening_spheres": post_opening_wide,
            "early_post_opening_spheres": early_post_opening_wide,
        },
        "progression_dilution": {
            "median_checks_per_progression_item": (
                median(ratios) if ratios else None
            ),
            "max_checks_per_progression_item": (
                max(ratios) if ratios else None
            ),
            "median_checks_per_sendable_progression_item": (
                median(sendable_ratios) if sendable_ratios else None
            ),
            "max_checks_per_sendable_progression_item": (
                max(sendable_ratios) if sendable_ratios else None
            ),
            "spheres": dilution,
            "sendable_spheres": sendable_dilution,
        },
    }
