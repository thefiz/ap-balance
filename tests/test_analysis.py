from apbalance.analysis import analyze_single_seed


def test_single_seed_analysis():
    spheres = [
        {"checks": 32, "progression_items": 13},
        {"checks": 37, "progression_items": 20},
        {"checks": 15, "progression_items": 7},
        {"checks": 2, "progression_items": 1},
        {"checks": 5, "progression_items": 0},
    ]
    result = analyze_single_seed(spheres)

    assert result["sphere_width"]["max"] == 37
    assert result["sphere_width"]["min"] == 2
    assert result["early_workload"]["checks_through_sphere_2"] == 84
    assert result["thin_spheres"]["count"] == 1
    assert result["wide_spheres"]["count"] == 2
    assert result["wide_spheres"]["early_count"] == 2
    assert result["progression_dilution"]["spheres"][3]["checks_per_progression_item"] == 2.0
    assert result["progression_dilution"]["spheres"][4]["checks_per_progression_item"] is None
