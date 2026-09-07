import importlib.util
from pathlib import Path


WORKER = Path(__file__).parents[1] / "apbalance" / "_ap_worker.py"


def load_worker():
    spec = importlib.util.spec_from_file_location("apbalance_worker_test", WORKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_fallback_prefers_progression_event():
    worker = load_worker()
    spheres = [
        {
            "index": 0,
            "locations": [
                {
                    "player": 1,
                    "sendable": True,
                    "progression": False,
                    "item_player": 1,
                }
            ],
        },
        {
            "index": 1,
            "locations": [
                {
                    "player": 1,
                    "sendable": False,
                    "progression": True,
                    "item_player": 1,
                }
            ],
        },
    ]

    step, detection = worker._fallback_completion_step(spheres, 1)
    assert step == 1
    assert detection == "last_progression_event_proxy"


def test_fallback_uses_last_sendable_when_no_event():
    worker = load_worker()
    spheres = [
        {
            "index": 0,
            "locations": [
                {
                    "player": 1,
                    "sendable": True,
                    "progression": False,
                    "item_player": 2,
                }
            ],
        },
        {
            "index": 2,
            "locations": [
                {
                    "player": 1,
                    "sendable": True,
                    "progression": False,
                    "item_player": 2,
                }
            ],
        },
    ]

    step, detection = worker._fallback_completion_step(spheres, 1)
    assert step == 2
    assert detection == "last_sendable_check_proxy"



def test_completion_detector_does_not_unrestricted_sweep():
    source = WORKER.read_text(encoding="utf-8")
    start = source.index("def completion_steps_from_spheres")
    end = source.index("def timeline_analysis", start)
    function_source = source[start:end]
    assert "sweep_for_advancements" not in function_source
