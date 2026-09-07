from __future__ import annotations

from statistics import mean, median
from typing import Any


EARLY_SPHERE_COUNT = 5
RELATIVE_WIDE_MULTIPLIER = 2.5
RELATIVE_THIN_MULTIPLIER = 0.35
CONCENTRATION_TOP_N = 3


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


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 3)


def analyze_single_seed(
    spheres: list[dict[str, Any]],
    *,
    early_sphere_count: int = EARLY_SPHERE_COUNT,
    relative_wide_multiplier: float = RELATIVE_WIDE_MULTIPLIER,
    relative_thin_multiplier: float = RELATIVE_THIN_MULTIPLIER,
    concentration_top_n: int = CONCENTRATION_TOP_N,
) -> dict[str, Any]:
    widths = _sphere_widths(spheres)
    progression = _progression_counts(spheres)
    sendable_progression = _sendable_progression_counts(spheres)

    if not widths:
        return {}

    terminal_index = len(widths) - 1
    nonterminal_widths = widths[:-1] if len(widths) > 1 else widths[:]
    typical_width = median(nonterminal_widths) if nonterminal_widths else median(widths)
    total_checks = sum(widths)

    relative_wide = []
    relative_thin = []

    for index, width in enumerate(widths):
        terminal = index == terminal_index
        ratio = _safe_ratio(width, typical_width)

        if not terminal and ratio is not None and ratio >= relative_wide_multiplier:
            relative_wide.append({
                "index": index,
                "checks": width,
                "relative_to_typical": ratio,
                "share_of_all_checks": _safe_ratio(width, total_checks),
                "progression_items": progression[index],
                "sendable_progression_items": sendable_progression[index],
            })

        if not terminal and ratio is not None and ratio <= relative_thin_multiplier:
            relative_thin.append({
                "index": index,
                "checks": width,
                "relative_to_typical": ratio,
                "progression_items": progression[index],
                "sendable_progression_items": sendable_progression[index],
            })

    thin_indices = [entry["index"] for entry in relative_thin]
    thin_runs = _consecutive_runs(thin_indices)

    sorted_widths = sorted(
        enumerate(widths),
        key=lambda pair: pair[1],
        reverse=True,
    )
    top = sorted_widths[: min(concentration_top_n, len(sorted_widths))]
    top_checks = sum(width for _, width in top)

    width_changes = [
        abs(widths[i] - widths[i - 1])
        for i in range(1, len(widths))
    ]
    relative_changes = [
        abs(widths[i] - widths[i - 1]) / typical_width
        for i in range(1, len(widths))
        if typical_width
    ]

    cumulative = _cumulative(widths)
    early_limit = min(early_sphere_count, len(widths))

    dilution = []
    sendable_dilution = []
    for index, (width, prog, sendable_prog) in enumerate(
        zip(widths, progression, sendable_progression)
    ):
        dilution.append({
            "index": index,
            "checks": width,
            "progression_items": prog,
            "checks_per_progression_item": _safe_ratio(width, prog),
        })
        sendable_dilution.append({
            "index": index,
            "checks": width,
            "sendable_progression_items": sendable_prog,
            "checks_per_sendable_progression_item": _safe_ratio(width, sendable_prog),
        })

    dilution_values = [
        x["checks_per_progression_item"]
        for x in dilution
        if x["checks_per_progression_item"] is not None
    ]
    sendable_dilution_values = [
        x["checks_per_sendable_progression_item"]
        for x in sendable_dilution
        if x["checks_per_sendable_progression_item"] is not None
    ]

    return {
        "sphere_width": {
            "count": len(widths),
            "min": min(widths),
            "max": max(widths),
            "mean": round(mean(widths), 3),
            "median": median(widths),
            "nonterminal_median": typical_width,
            "largest_sphere_index": widths.index(max(widths)),
            "smallest_sphere_index": widths.index(min(widths)),
            "largest_to_typical_ratio": _safe_ratio(max(widths), typical_width),
        },
        "workload_concentration": {
            "largest_sphere_share": _safe_ratio(max(widths), total_checks),
            "top_n": len(top),
            "top_n_share": _safe_ratio(top_checks, total_checks),
            "top_spheres": [
                {
                    "index": index,
                    "checks": width,
                    "share_of_all_checks": _safe_ratio(width, total_checks),
                }
                for index, width in top
            ],
        },
        "relative_wide_spheres": {
            "threshold_multiplier": relative_wide_multiplier,
            "count": len(relative_wide),
            "spheres": relative_wide,
            "max_relative_width": max(
                (entry["relative_to_typical"] for entry in relative_wide),
                default=0,
            ),
        },
        "relative_thin_spheres": {
            "threshold_multiplier": relative_thin_multiplier,
            "count": len(relative_thin),
            "spheres": relative_thin,
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
        "pacing_volatility": {
            "mean_absolute_width_change": (
                round(mean(width_changes), 3) if width_changes else 0
            ),
            "mean_relative_width_change": (
                round(mean(relative_changes), 3) if relative_changes else 0
            ),
            "max_relative_width_change": (
                round(max(relative_changes), 3) if relative_changes else 0
            ),
        },
        "early_workload": {
            "sphere_count_considered": early_limit,
            "checks_through_sphere_0": cumulative[0],
            "checks_through_sphere_1": cumulative[min(1, len(cumulative) - 1)],
            "checks_through_sphere_2": cumulative[min(2, len(cumulative) - 1)],
            "checks_through_sphere_4": cumulative[min(4, len(cumulative) - 1)],
            "share_through_sphere_1": _safe_ratio(
                cumulative[min(1, len(cumulative) - 1)], total_checks
            ),
            "share_through_sphere_2": _safe_ratio(
                cumulative[min(2, len(cumulative) - 1)], total_checks
            ),
            "share_through_sphere_4": _safe_ratio(
                cumulative[min(4, len(cumulative) - 1)], total_checks
            ),
        },
        "progression_dilution": {
            "median_checks_per_progression_item": (
                median(dilution_values) if dilution_values else None
            ),
            "max_checks_per_progression_item": (
                max(dilution_values) if dilution_values else None
            ),
            "median_checks_per_sendable_progression_item": (
                median(sendable_dilution_values) if sendable_dilution_values else None
            ),
            "max_checks_per_sendable_progression_item": (
                max(sendable_dilution_values) if sendable_dilution_values else None
            ),
            "spheres": dilution,
            "sendable_spheres": sendable_dilution,
        },
    }
