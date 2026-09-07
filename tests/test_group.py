from pathlib import Path
import apbalance.group as group_module


def _event(checks, ratio, waiting=1, external=2):
    return {
        "step": 1,
        "host": 1,
        "host_sendable_checks": checks,
        "active_peer_median_sendable_checks": checks / ratio,
        "workload_ratio_to_active_peer_median": ratio,
        "waiting_players": [2],
        "waiting_player_count": waiting,
        "external_progression_for_waiting_players": external,
    }


def _player(pressure, starvation, finish, peers, released):
    return {
        "progression_bottleneck": {
            "event_count": len(pressure),
            "events": pressure,
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
            "released_checks": released,
            "released_progression_items": max(0, released // 5),
            "released_external_progression_items": max(0, released // 10),
            "recipient_players": [2] if released else [],
            "recipient_player_count": 1 if released else 0,
            "release_checks_ratio_to_active_peer_median": released / 10 if released else 0,
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
                "1": _player([_event(40, 4.0)], 0, 0.4, 1.0, 50),
                "2": _player([], 2, 1.0, 0.0, 0),
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
    assert result["rankings"]["progression_bottleneck"][0]["name"] == "A"
    assert result["rankings"]["early_completion"][0]["name"] == "A"
    assert result["rankings"]["check_starvation"][0]["name"] == "B"
    assert result["rankings"]["early_release"][0]["name"] == "A"
    assert result["players"][0]["progression_bottleneck"]["seed_frequency"] == 1.0
    assert result["players"][1]["check_starvation"]["seed_frequency"] == 1.0
    assert len(result["analysis_assumptions"]) == 3
