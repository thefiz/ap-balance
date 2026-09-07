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


def _cumulative(values: list[int]) -> list[int]:
    total = 0
    result = []
    for value in values:
        total += value
        result.append(total)
    return result


def analyze_single_seed(
    spheres: list[dict[str, Any]],
    *,
    thin_sphere_max: int = DEFAULT_THIN_SPHERE_MAX,
    wide_sphere_min: int = DEFAULT_WIDE_SPHERE_MIN,
    early_sphere_count: int = EARLY_SPHERE_COUNT,
) -> dict[str, Any]:
    widths = _sphere_widths(spheres)
    progression = _progression_counts(spheres)
    cumulative_checks = _cumulative(widths)

    if not widths:
        return {
            "sphere_width": {},
            "early_workload": {},
            "thin_spheres": [],
            "wide_spheres": [],
            "progression_dilution": [],
        }

    thin = [
        {
            "index": index,
            "checks": width,
            "progression_items": progression[index],
        }
        for index, width in enumerate(widths)
        if width <= thin_sphere_max
    ]

    wide = [
        {
            "index": index,
            "checks": width,
            "progression_items": progression[index],
            "early": index < early_sphere_count,
        }
        for index, width in enumerate(widths)
        if width >= wide_sphere_min
    ]

    dilution = []
    for index, (width, prog) in enumerate(zip(widths, progression)):
        dilution.append({
            "index": index,
            "checks": width,
            "progression_items": prog,
            "checks_per_progression_item": (
                round(width / prog, 3) if prog > 0 else None
            ),
        })

    early_limit = min(early_sphere_count, len(widths))
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
            "count": len(thin),
            "spheres": thin,
        },
        "wide_spheres": {
            "threshold_min_checks": wide_sphere_min,
            "count": len(wide),
            "early_count": sum(1 for entry in wide if entry["early"]),
            "spheres": wide,
        },
        "progression_dilution": {
            "median_checks_per_progression_item": (
                median(ratios) if ratios else None
            ),
            "max_checks_per_progression_item": (
                max(ratios) if ratios else None
            ),
            "spheres": dilution,
        },
    }
