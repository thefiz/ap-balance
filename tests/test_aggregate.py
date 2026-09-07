from apbalance.aggregate import summarize, aggregate_samples


def test_summarize():
    result = summarize([1, 2, 3, 4, 5])
    assert result["median"] == 3
    assert result["mean"] == 3


def test_aggregate_relative_metrics():
    sample = {
        "world": {"locations_total": 100},
        "logical_spheres": {"count": 10},
        "analysis": {
            "sphere_width": {"largest_to_typical_ratio": 3.0},
            "workload_concentration": {
                "largest_sphere_share": 0.25,
                "top_n_share": 0.55,
            },
            "relative_wide_spheres": {"count": 1},
            "relative_thin_spheres": {
                "count": 2,
                "longest_consecutive_run": 2,
            },
            "pacing_volatility": {
                "mean_relative_width_change": 0.8,
                "max_relative_width_change": 2.2,
            },
            "early_workload": {
                "share_through_sphere_2": 0.30,
                "share_through_sphere_4": 0.45,
            },
            "progression_dilution": {
                "median_checks_per_sendable_progression_item": 2.5,
                "max_checks_per_sendable_progression_item": 7.0,
            },
        },
    }

    result = aggregate_samples([sample, sample])

    assert result["relative_pacing"]["relative_wide_frequency"] == 1.0
    assert result["relative_pacing"]["relative_thin_frequency"] == 1.0
    assert result["relative_pacing"]["consecutive_thin_frequency"] == 1.0
    assert result["relative_pacing"]["largest_to_typical_ratio"]["median"] == 3
