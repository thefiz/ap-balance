from apbalance.analysis import analyze_single_seed


def test_single_seed_analysis():
    spheres = [
        {
            "checks": 32,
            "progression_items": 13,
            "locations": [{"progression": True, "sendable": True}] * 10,
        },
        {
            "checks": 37,
            "progression_items": 20,
            "locations": [{"progression": True, "sendable": True}] * 15,
        },
        {
            "checks": 3,
            "progression_items": 2,
            "locations": [{"progression": True, "sendable": True}] * 2,
        },
        {
            "checks": 2,
            "progression_items": 1,
            "locations": [{"progression": True, "sendable": True}],
        },
        {
            "checks": 1,
            "progression_items": 1,
            "locations": [{"progression": True, "sendable": False}],
        },
    ]
    result = analyze_single_seed(spheres)

    assert result["sphere_width"]["max"] == 37
    assert result["sphere_width"]["min"] == 1
    assert result["early_workload"]["checks_through_sphere_2"] == 72
    assert result["thin_spheres"]["mid_progression_count"] == 2
    assert result["thin_spheres"]["terminal_count"] == 1
    assert result["thin_spheres"]["longest_consecutive_run"] == 2
    assert result["wide_spheres"]["opening_count"] == 1
    assert result["wide_spheres"]["post_opening_count"] == 1
    assert result["wide_spheres"]["early_post_opening_count"] == 1
    assert (
        result["progression_dilution"]["spheres"][3]["checks_per_progression_item"]
        == 2.0
    )
