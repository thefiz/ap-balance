from __future__ import annotations

from math import sqrt
from statistics import mean, median
from typing import Any


def percentile(sorted_values: list[float], p: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (len(sorted_values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    fraction = rank - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * fraction


def summarize(values: list[float | int]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "p10": None,
            "p25": None,
            "median": None,
            "mean": None,
            "p75": None,
            "p90": None,
            "max": None,
            "stddev": None,
        }

    nums = [float(v) for v in values]
    ordered = sorted(nums)
    avg = mean(nums)
    variance = mean([(v - avg) ** 2 for v in nums])

    def clean(v):
        if v is None:
            return None
        if float(v).is_integer():
            return int(v)
        return round(v, 3)

    return {
        "count": len(nums),
        "min": clean(ordered[0]),
        "p10": clean(percentile(ordered, 0.10)),
        "p25": clean(percentile(ordered, 0.25)),
        "median": clean(median(ordered)),
        "mean": clean(avg),
        "p75": clean(percentile(ordered, 0.75)),
        "p90": clean(percentile(ordered, 0.90)),
        "max": clean(ordered[-1]),
        "stddev": clean(sqrt(variance)),
    }


def aggregate_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {"samples": 0}

    sphere_counts = [s["logical_spheres"]["count"] for s in samples]
    total_locations = [s["world"]["locations_total"] for s in samples]
    progression_items = [s["world"]["progression_items"] for s in samples]

    largest_spheres = [s["analysis"]["sphere_width"]["max"] for s in samples]
    smallest_spheres = [s["analysis"]["sphere_width"]["min"] for s in samples]

    opening_spheres = [
        s["analysis"]["early_workload"]["checks_through_sphere_0"]
        for s in samples
    ]
    through_1 = [
        s["analysis"]["early_workload"]["checks_through_sphere_1"]
        for s in samples
    ]
    through_2 = [
        s["analysis"]["early_workload"]["checks_through_sphere_2"]
        for s in samples
    ]
    through_4 = [
        s["analysis"]["early_workload"]["checks_through_sphere_4"]
        for s in samples
    ]

    mid_thin_counts = [
        s["analysis"]["thin_spheres"]["mid_progression_count"] for s in samples
    ]
    terminal_thin_counts = [
        s["analysis"]["thin_spheres"]["terminal_count"] for s in samples
    ]
    longest_thin_runs = [
        s["analysis"]["thin_spheres"]["longest_consecutive_run"] for s in samples
    ]

    post_opening_wide_counts = [
        s["analysis"]["wide_spheres"]["post_opening_count"] for s in samples
    ]
    early_post_opening_wide_counts = [
        s["analysis"]["wide_spheres"]["early_post_opening_count"] for s in samples
    ]

    dilution_medians = [
        s["analysis"]["progression_dilution"]["median_checks_per_progression_item"]
        for s in samples
        if s["analysis"]["progression_dilution"]["median_checks_per_progression_item"] is not None
    ]
    dilution_maxes = [
        s["analysis"]["progression_dilution"]["max_checks_per_progression_item"]
        for s in samples
        if s["analysis"]["progression_dilution"]["max_checks_per_progression_item"] is not None
    ]
    sendable_dilution_medians = [
        s["analysis"]["progression_dilution"]["median_checks_per_sendable_progression_item"]
        for s in samples
        if s["analysis"]["progression_dilution"]["median_checks_per_sendable_progression_item"] is not None
    ]
    sendable_dilution_maxes = [
        s["analysis"]["progression_dilution"]["max_checks_per_sendable_progression_item"]
        for s in samples
        if s["analysis"]["progression_dilution"]["max_checks_per_sendable_progression_item"] is not None
    ]

    return {
        "samples": len(samples),
        "world": {
            "locations_total": summarize(total_locations),
            "progression_items": summarize(progression_items),
        },
        "sphere_count": summarize(sphere_counts),
        "sphere_width": {
            "largest": summarize(largest_spheres),
            "smallest": summarize(smallest_spheres),
        },
        "early_workload": {
            "sphere_0": summarize(opening_spheres),
            "through_sphere_1": summarize(through_1),
            "through_sphere_2": summarize(through_2),
            "through_sphere_4": summarize(through_4),
        },
        "thin_spheres": {
            "mid_progression_count_per_seed": summarize(mid_thin_counts),
            "terminal_count_per_seed": summarize(terminal_thin_counts),
            "longest_consecutive_run": summarize(longest_thin_runs),
            "seeds_with_mid_progression_thin": sum(1 for v in mid_thin_counts if v > 0),
            "mid_progression_frequency": round(
                sum(1 for v in mid_thin_counts if v > 0) / len(samples), 3
            ),
            "seeds_with_consecutive_thin": sum(1 for v in longest_thin_runs if v >= 2),
            "consecutive_frequency": round(
                sum(1 for v in longest_thin_runs if v >= 2) / len(samples), 3
            ),
        },
        "wide_spheres": {
            "post_opening_count_per_seed": summarize(post_opening_wide_counts),
            "early_post_opening_count_per_seed": summarize(early_post_opening_wide_counts),
            "seeds_with_post_opening_wide": sum(1 for v in post_opening_wide_counts if v > 0),
            "post_opening_frequency": round(
                sum(1 for v in post_opening_wide_counts if v > 0) / len(samples), 3
            ),
            "seeds_with_early_post_opening_wide": sum(
                1 for v in early_post_opening_wide_counts if v > 0
            ),
            "early_post_opening_frequency": round(
                sum(1 for v in early_post_opening_wide_counts if v > 0) / len(samples), 3
            ),
        },
        "progression_dilution": {
            "median_checks_per_progression_item": summarize(dilution_medians),
            "max_checks_per_progression_item": summarize(dilution_maxes),
            "median_checks_per_sendable_progression_item": summarize(sendable_dilution_medians),
            "max_checks_per_sendable_progression_item": summarize(sendable_dilution_maxes),
        },
    }
