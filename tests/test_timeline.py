import importlib.util
from pathlib import Path


WORKER = Path(__file__).parents[1] / "apbalance" / "_ap_worker.py"


def load_worker():
    spec = importlib.util.spec_from_file_location("apbalance_worker_timeline_test", WORKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def loc(host, recipient, progression=True, sendable=True):
    return {
        "name": "x",
        "player": host,
        "item": "item",
        "item_player": recipient,
        "progression": progression,
        "sendable": sendable,
    }


def test_release_payload_counts_only_post_goal_hosted_checks():
    worker = load_worker()
    spheres = [
        {"index": 0, "locations": [loc(1, 2)]},
        {"index": 1, "locations": [loc(1, 2), loc(2, 1)]},
        {"index": 2, "locations": [loc(1, 2), loc(1, 1, progression=False)]},
    ]

    payload = worker._release_payload(spheres, 1, 1)
    assert payload["released_checks"] == 2
    assert payload["released_progression_items"] == 1
    assert payload["released_external_progression_items"] == 1
    assert payload["recipient_players"] == [2]


def test_post_goal_host_workload_is_zeroed_and_not_starvation():
    worker = load_worker()

    class MW:
        players = 2

    spheres = [
        {
            "index": 0,
            "locations": [loc(1, 2), loc(2, 1)],
        },
        {
            "index": 1,
            "locations": [loc(1, 2), loc(2, 1)],
        },
    ]
    result = worker.timeline_analysis(
        MW(),
        spheres,
        {1: 0, 2: 1},
        {1: "archipelago_completion_condition", 2: "archipelago_completion_condition"},
    )

    assert result["steps"][1]["effective_checks_by_player"]["1"] == 0
    assert 1 not in result["steps"][1]["check_starved_unfinished_players"]
    assert result["players"]["1"]["early_release"]["released_checks"] == 1


def test_dependency_event_has_group_relative_workload_ratio():
    worker = load_worker()

    class MW:
        players = 3

    spheres = [
        {
            "index": 0,
            "locations": (
                [loc(1, 3)] * 6
                + [loc(2, 1, progression=False)] * 2
            ),
        }
    ]
    result = worker.timeline_analysis(
        MW(),
        spheres,
        {1: 0, 2: 0, 3: 0},
        {
            1: "archipelago_completion_condition",
            2: "archipelago_completion_condition",
            3: "archipelago_completion_condition",
        },
    )

    events = result["players"]["1"]["progression_bottleneck"]["events"]
    assert len(events) == 1
    assert events[0]["waiting_players"] == [3]
    assert events[0]["workload_ratio_to_active_peer_median"] == 3.0
