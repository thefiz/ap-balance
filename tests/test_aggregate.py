from apbalance.aggregate import summarize, aggregate_samples


def test_summarize():
    result = summarize([1, 2, 3, 4, 5])
    assert result["min"] == 1
    assert result["median"] == 3
    assert result["max"] == 5
    assert result["mean"] == 3


def test_aggregate_samples():
    sample = {
        "world": {"locations_total": 100, "progression_items": 20},
        "logical_spheres": {"count": 10},
        "analysis": {
            "sphere_width": {"max": 30, "min": 1},
            "early_workload": {
                "checks_through_sphere_0": 20,
                "checks_through_sphere_1": 35,
                "checks_through_sphere_2": 50,
                "checks_through_sphere_4": 75,
            },
            "thin_spheres": {
                "mid_progression_count": 2,
                "terminal_count": 1,
                "longest_consecutive_run": 2,
            },
            "wide_spheres": {
                "post_opening_count": 1,
                "early_post_opening_count": 1,
            },
            "progression_dilution": {
                "median_checks_per_progression_item": 3.0,
                "max_checks_per_progression_item": 5.0,
                "median_checks_per_sendable_progression_item": 4.0,
                "max_checks_per_sendable_progression_item": 8.0,
            },
        },
    }
    result = aggregate_samples([sample, sample])
    assert result["samples"] == 2
    assert result["sphere_count"]["median"] == 10
    assert result["thin_spheres"]["mid_progression_frequency"] == 1.0
    assert result["thin_spheres"]["consecutive_frequency"] == 1.0
    assert result["wide_spheres"]["early_post_opening_frequency"] == 1.0
