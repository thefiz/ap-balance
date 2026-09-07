from apbalance.analysis import analyze_single_seed


def make_sphere(checks, progression=1, sendable=1):
    return {
        "checks": checks,
        "progression_items": progression,
        "locations": (
            [{"progression": True, "sendable": True}] * sendable
            + [{"progression": False, "sendable": True}] * max(0, checks - sendable)
        ),
    }


def test_relative_pacing_metrics():
    spheres = [
        make_sphere(10, 4, 3),
        make_sphere(12, 5, 4),
        make_sphere(40, 10, 8),
        make_sphere(3, 1, 1),
        make_sphere(2, 1, 1),
        make_sphere(1, 1, 0),  # terminal
    ]

    result = analyze_single_seed(spheres)

    assert result["sphere_width"]["nonterminal_median"] == 10
    assert result["sphere_width"]["largest_to_typical_ratio"] == 4.0
    assert result["relative_wide_spheres"]["count"] == 1
    assert result["relative_wide_spheres"]["spheres"][0]["index"] == 2
    assert result["relative_thin_spheres"]["count"] == 2
    assert result["relative_thin_spheres"]["longest_consecutive_run"] == 2
    assert result["workload_concentration"]["largest_sphere_share"] == 0.588
    assert result["early_workload"]["share_through_sphere_2"] == 0.912
