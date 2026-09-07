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
    locations = [s["world"]["locations_total"] for s in samples]

    largest_to_typical = [
        s["analysis"]["sphere_width"]["largest_to_typical_ratio"] for s in samples
    ]
    largest_share = [
        s["analysis"]["workload_concentration"]["largest_sphere_share"] for s in samples
    ]
    top_n_share = [
        s["analysis"]["workload_concentration"]["top_n_share"] for s in samples
    ]
    relative_wide_counts = [
        s["analysis"]["relative_wide_spheres"]["count"] for s in samples
    ]
    relative_thin_counts = [
        s["analysis"]["relative_thin_spheres"]["count"] for s in samples
    ]
    longest_thin_runs = [
        s["analysis"]["relative_thin_spheres"]["longest_consecutive_run"] for s in samples
    ]
    volatility_mean = [
        s["analysis"]["pacing_volatility"]["mean_relative_width_change"] for s in samples
    ]
    volatility_max = [
        s["analysis"]["pacing_volatility"]["max_relative_width_change"] for s in samples
    ]
    early_share_2 = [
        s["analysis"]["early_workload"]["share_through_sphere_2"] for s in samples
    ]
    early_share_4 = [
        s["analysis"]["early_workload"]["share_through_sphere_4"] for s in samples
    ]
    sendable_dilution_median = [
        s["analysis"]["progression_dilution"]["median_checks_per_sendable_progression_item"]
        for s in samples
        if s["analysis"]["progression_dilution"]["median_checks_per_sendable_progression_item"] is not None
    ]
    sendable_dilution_max = [
        s["analysis"]["progression_dilution"]["max_checks_per_sendable_progression_item"]
        for s in samples
        if s["analysis"]["progression_dilution"]["max_checks_per_sendable_progression_item"] is not None
    ]

    return {
        "samples": len(samples),
        "world": {
            "locations_total": summarize(locations),
        },
        "sphere_count": summarize(sphere_counts),
        "relative_pacing": {
            "largest_to_typical_ratio": summarize(largest_to_typical),
            "largest_sphere_share": summarize(largest_share),
            "top_sphere_share": summarize(top_n_share),
            "relative_wide_count_per_seed": summarize(relative_wide_counts),
            "relative_thin_count_per_seed": summarize(relative_thin_counts),
            "longest_consecutive_thin_run": summarize(longest_thin_runs),
            "mean_relative_width_change": summarize(volatility_mean),
            "max_relative_width_change": summarize(volatility_max),
            "early_share_through_sphere_2": summarize(early_share_2),
            "early_share_through_sphere_4": summarize(early_share_4),
            "seeds_with_relative_wide": sum(1 for v in relative_wide_counts if v > 0),
            "relative_wide_frequency": round(
                sum(1 for v in relative_wide_counts if v > 0) / len(samples), 3
            ),
            "seeds_with_relative_thin": sum(1 for v in relative_thin_counts if v > 0),
            "relative_thin_frequency": round(
                sum(1 for v in relative_thin_counts if v > 0) / len(samples), 3
            ),
            "seeds_with_consecutive_thin": sum(1 for v in longest_thin_runs if v >= 2),
            "consecutive_thin_frequency": round(
                sum(1 for v in longest_thin_runs if v >= 2) / len(samples), 3
            ),
        },
        "progression_dilution": {
            "median_checks_per_sendable_progression_item": summarize(sendable_dilution_median),
            "max_checks_per_sendable_progression_item": summarize(sendable_dilution_max),
        },
    }
