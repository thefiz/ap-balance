from pathlib import Path
import apbalance.group as group_module


def _event(checks, ratio, candidate=True, waiting=1, external=2):
    return {
        "step": 1,
        "host": 1,
        "host_sendable_checks": checks,
        "active_peer_median_sendable_checks": checks / ratio,
        "workload_ratio_to_active_peer_median": ratio,
        "host_is_unique_highest_active_workload": candidate,
        "waiting_players": [2],
        "waiting_player_count": waiting,
        "external_progression_for_waiting_players": external,
    }


def _player(events, starvation, finish, peers, release_expected):
    candidates = [
        event for event in events
        if event["host_is_unique_highest_active_workload"]
    ]
    return {
        "progression_bottleneck": {
            "dependency_event_count": len(events),
            "dependency_events": events,
            "candidate_event_count": len(candidates),
            "candidate_events": candidates,
        },
        "early_completion": {
            "completion_step": 2,
            "completion_position": finish,
            "peers_still_active_fraction": peers,
            "completion_detection": "archipelago_completion_condition",
        },
        "check_starvation": {
            "starvation_step_count": starvation,
            "starvation_steps": list(range(starvation)),
            "eligible_steps_before_completion": 4,
            "starvation_fraction_before_completion": starvation / 4,
            "longest_starvation_streak": starvation,
        },
        "early_release": {
            "released_checks_min": max(0, release_expected - 5),
            "released_checks_expected": release_expected,
            "released_checks_max": release_expected + 5,
            "released_progression_items_min": 1,
            "released_progression_items_expected": 2,
            "released_progression_items_max": 3,
            "released_external_progression_items_min": 1,
            "released_external_progression_items_expected": 2,
            "released_external_progression_items_max": 3,
            "recipient_players_min": [2],
            "recipient_players_max": [2],
            "recipient_player_count_min": 1,
            "recipient_player_count_max": 1,
            "completion_sphere_hosted_checks": 10,
            "release_checks_ratio_to_active_peer_median_min": 1.0,
            "release_checks_ratio_to_active_peer_median_expected": 2.0,
            "release_checks_ratio_to_active_peer_median_max": 3.0,
            "early_release_index": (1 - finish) * 2.0,
        },
    }


def _sample(seed):
    return {
        "archipelago_version": "test",
        "seed": seed,
        "seed_name": str(seed),
        "players": [
            {"id": 1, "name": "A", "game": "Game A"},
            {"id": 2, "name": "B", "game": "Game B"},
        ],
        "timeline_analysis": {
            "players": {
                "1": _player([_event(40, 4.0, True)], 0, 0.4, 1.0, 50),
                "2": _player([_event(10, 0.5, False)], 2, 1.0, 0.0, 0),
            }
        },
    }


def test_group_rankings(monkeypatch):
    samples = [_sample(1), _sample(2)]

    def fake_inspect_group(**kwargs):
        return samples.pop(0)

    monkeypatch.setattr(group_module, "inspect_group", fake_inspect_group)

    result = group_module.analyze_group(
        Path("."),
        Path("."),
        samples=2,
        base_seed=123,
    )

    assert result["schema_version"] == 2
    assert result["analyzer_version"] == "0.9.1"
    assert result["rankings"]["progression_bottleneck"][0]["name"] == "A"
    assert result["rankings"]["early_completion"][0]["name"] == "A"
    assert result["rankings"]["check_starvation"][0]["name"] == "B"
    assert result["rankings"]["early_release"][0]["name"] == "A"
    assert result["players"][0]["progression_bottleneck"]["bottleneck_candidate_seed_frequency"] == 1.0
    assert result["players"][1]["progression_bottleneck"]["bottleneck_candidate_seed_frequency"] == 0.0
    assert len(result["analysis_assumptions"]) == 3
