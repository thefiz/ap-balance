from pathlib import Path
import apbalance.group as group_module


def _sample(seed, p1_pressure, p2_pressure, p1_idle, p2_idle, p1_finish, p2_finish):
    return {
        "archipelago_version": "test",
        "seed": seed,
        "seed_name": str(seed),
        "players": [
            {"id": 1, "name": "A", "game": "Game A", "world": {"locations_sendable": 100}},
            {"id": 2, "name": "B", "game": "Game B", "world": {"locations_sendable": 100}},
        ],
        "timeline_analysis": {
            "players": {
                "1": {
                    "progression_pressure": {
                        "event_count": len(p1_pressure),
                        "events": p1_pressure,
                    },
                    "early_completion": {
                        "completion_step": 2,
                        "completion_position": p1_finish,
                        "peers_still_active_fraction": 1.0 if p1_finish < p2_finish else 0.0,
                        "completion_detection": "archipelago_completion_condition",
                    },
                    "idle": {
                        "idle_step_count": p1_idle,
                        "idle_steps": list(range(p1_idle)),
                        "eligible_steps_before_completion": 4,
                        "idle_fraction_before_completion": p1_idle / 4,
                        "longest_idle_streak": p1_idle,
                    },
                },
                "2": {
                    "progression_pressure": {
                        "event_count": len(p2_pressure),
                        "events": p2_pressure,
                    },
                    "early_completion": {
                        "completion_step": 4,
                        "completion_position": p2_finish,
                        "peers_still_active_fraction": 1.0 if p2_finish < p1_finish else 0.0,
                        "completion_detection": "archipelago_completion_condition",
                    },
                    "idle": {
                        "idle_step_count": p2_idle,
                        "idle_steps": list(range(p2_idle)),
                        "eligible_steps_before_completion": 5,
                        "idle_fraction_before_completion": p2_idle / 5,
                        "longest_idle_streak": p2_idle,
                    },
                },
            }
        },
    }


def _event(checks, waiting=1, external=2):
    return {
        "step": 1,
        "host": 1,
        "host_sendable_checks": checks,
        "waiting_players": [2],
        "waiting_player_count": waiting,
        "external_progression_for_waiting_players": external,
    }


def test_group_rankings(monkeypatch):
    samples = [
        _sample(1, [_event(40)], [], 0, 2, 0.5, 1.0),
        _sample(2, [_event(50)], [], 0, 1, 0.5, 1.0),
    ]

    def fake_inspect_group(**kwargs):
        return samples.pop(0)

    monkeypatch.setattr(group_module, "inspect_group", fake_inspect_group)

    result = group_module.analyze_group(
        Path("."),
        Path("."),
        samples=2,
        base_seed=123,
    )

    assert result["mode"] == "group_multi_seed"
    assert result["rankings"]["progression_pressure"][0]["name"] == "A"
    assert result["rankings"]["early_completion"][0]["name"] == "A"
    assert result["rankings"]["idle"][0]["name"] == "B"
    assert result["players"][0]["progression_pressure"]["seed_frequency"] == 1.0
    assert result["players"][1]["idle"]["seed_frequency"] == 1.0
    assert "Players are assumed" in result["analysis_assumption"]
