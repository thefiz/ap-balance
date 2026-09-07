from __future__ import annotations

# This module is intentionally executed as a fresh child process.
# Archipelago's worlds package indexes core/custom worlds at import time, so
# starting clean is important when staging an .apworld.

import argparse
import json
import logging
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archipelago", type=Path, required=True)
    parser.add_argument("--players", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--multi", type=int, default=1)
    parser.add_argument("--group", action="store_true")
    return parser.parse_args()


def is_sendable(location) -> bool:
    return (
        location.item is not None
        and type(location.address) is int
        and type(location.item.code) is int
    )


def progression_count(locations) -> int:
    return sum(
        1 for location in locations
        if location.item is not None and bool(location.item.advancement)
    )


def serialize_spheres(spheres) -> tuple[list[dict], int]:
    result: list[dict] = []
    unreachable = 0

    sphere_list = list(spheres)
    # Archipelago documents unreachable locations as:
    # reachable sphere -> empty sphere -> all unreachable locations.
    for index, sphere in enumerate(sphere_list):
        if not sphere:
            if index + 1 < len(sphere_list):
                unreachable += len(sphere_list[index + 1])
            continue

        # If immediately preceded by an empty sphere, this is the unreachable set,
        # not another normal logical sphere.
        if index > 0 and not sphere_list[index - 1]:
            continue

        sphere_locations = list(sphere)
        result.append({
            "index": len(result),
            "checks": len(sphere_locations),
            "progression_items": progression_count(sphere_locations),
            "sendable_checks": sum(1 for location in sphere_locations if is_sendable(location)),
            "locations": [
                {
                    "name": location.name,
                    "player": location.player,
                    "item": location.item.name if location.item else None,
                    "item_player": location.item.player if location.item else None,
                    "progression": bool(location.item and location.item.advancement),
                    "sendable": is_sendable(location),
                }
                for location in sorted(
                    sphere_locations,
                    key=lambda loc: (loc.player, loc.name)
                )
            ],
        })

    return result, unreachable





def _fallback_completion_step(logical_spheres, player: int) -> tuple[int | None, str]:
    """
    Prefer the last owned non-sendable progression event as a completion proxy.
    If none exists, fall back to the last sendable check in the player's world.
    """
    last_progression_event = None
    last_sendable = None

    for sphere in logical_spheres:
        for location in sphere["locations"]:
            if int(location["player"]) != player:
                continue

            if location["sendable"]:
                last_sendable = sphere["index"]
            elif (
                location["progression"]
                and location["item_player"] is not None
                and int(location["item_player"]) == player
            ):
                last_progression_event = sphere["index"]

    if last_progression_event is not None:
        return last_progression_event, "last_progression_event_proxy"
    if last_sendable is not None:
        return last_sendable, "last_sendable_check_proxy"
    return None, "completion_unavailable"


def completion_steps_from_spheres(
    multiworld,
    raw_spheres,
    logical_spheres,
) -> tuple[dict[int, int | None], dict[int, str]]:
    """
    Determine the first global logical sphere after which each player's
    Archipelago completion condition is satisfied.

    A completion condition that is already true on the initial CollectionState
    is treated as unusable for timeline analysis. Such players use an explicitly
    labeled structural fallback instead of being reported as complete at step -1.
    """
    player_ids = list(range(1, multiworld.players + 1))
    completion_steps = {player: None for player in player_ids}
    detection = {
        player: "archipelago_completion_condition"
        for player in player_ids
    }

    try:
        from BaseClasses import CollectionState
        state = CollectionState(multiworld)

        valid_condition = {}
        for player in player_ids:
            try:
                starts_complete = bool(multiworld.completion_condition[player](state))
            except Exception:
                starts_complete = True

            valid_condition[player] = not starts_complete
            if starts_complete:
                fallback_step, fallback_detection = _fallback_completion_step(
                    logical_spheres, player
                )
                completion_steps[player] = fallback_step
                detection[player] = fallback_detection

        normal_index = -1
        sphere_list = list(raw_spheres)

        for raw_index, sphere in enumerate(sphere_list):
            if not sphere:
                continue
            if raw_index > 0 and not sphere_list[raw_index - 1]:
                continue

            normal_index += 1

            for location in sphere:
                if location.item is None:
                    continue
                try:
                    state.collect(location.item, True, location)
                except TypeError:
                    try:
                        state.collect(location.item, True)
                    except TypeError:
                        state.collect(location.item)

            for player in player_ids:
                if not valid_condition[player]:
                    continue
                if completion_steps[player] is not None:
                    continue

                try:
                    if multiworld.completion_condition[player](state):
                        completion_steps[player] = normal_index
                except Exception:
                    valid_condition[player] = False

        # If an ostensibly valid completion condition never fired, use a labeled
        # fallback rather than silently returning no completion point.
        for player in player_ids:
            if completion_steps[player] is None:
                fallback_step, fallback_detection = _fallback_completion_step(
                    logical_spheres, player
                )
                completion_steps[player] = fallback_step
                detection[player] = fallback_detection

        return completion_steps, detection

    except Exception:
        for player in player_ids:
            fallback_step, fallback_detection = _fallback_completion_step(
                logical_spheres, player
            )
            completion_steps[player] = fallback_step
            detection[player] = fallback_detection
        return completion_steps, detection


def _median(values):
    values = sorted(values)
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return float(values[middle])
    return (values[middle - 1] + values[middle]) / 2


def _release_payload(logical_spheres, host: int, completion_step: int | None) -> dict:
    """
    Count sendable locations hosted by a player that occur strictly after that
    player's goal-completion sphere. Under the standard release-on-goal
    assumption, these become available immediately when the player completes.
    """
    if completion_step is None:
        return {
            "released_checks": 0,
            "released_progression_items": 0,
            "released_external_progression_items": 0,
            "recipient_players": [],
            "recipient_player_count": 0,
        }

    released_checks = 0
    released_progression = 0
    released_external_progression = 0
    recipients = set()

    for sphere in logical_spheres:
        if sphere["index"] <= completion_step:
            continue

        for location in sphere["locations"]:
            if not location["sendable"] or int(location["player"]) != host:
                continue

            released_checks += 1

            if location["progression"]:
                released_progression += 1
                if (
                    location["item_player"] is not None
                    and int(location["item_player"]) != host
                ):
                    released_external_progression += 1
                    recipients.add(int(location["item_player"]))

    return {
        "released_checks": released_checks,
        "released_progression_items": released_progression,
        "released_external_progression_items": released_external_progression,
        "recipient_players": sorted(recipients),
        "recipient_player_count": len(recipients),
    }


def timeline_analysis(multiworld, logical_spheres, completion_steps, completion_detection) -> dict:
    player_ids = list(range(1, multiworld.players + 1))
    total_steps = len(logical_spheres)

    player_events = {
        player: {
            "dependency_events": [],
            "starvation_steps": [],
        }
        for player in player_ids
    }

    release_payloads = {
        player: _release_payload(logical_spheres, player, completion_steps[player])
        for player in player_ids
    }

    rows = []

    for sphere in logical_spheres:
        step = sphere["index"]

        raw_checks_by_player = {player: 0 for player in player_ids}
        external_items_by_host_and_recipient = {
            player: {recipient: 0 for recipient in player_ids}
            for player in player_ids
        }

        for location in sphere["locations"]:
            if not location["sendable"]:
                continue

            host = int(location["player"])
            raw_checks_by_player[host] += 1

            if (
                location["progression"]
                and location["item_player"] is not None
                and int(location["item_player"]) != host
            ):
                recipient = int(location["item_player"])
                external_items_by_host_and_recipient[host][recipient] += 1

        completed_before = {
            player: (
                completion_steps[player] is not None
                and completion_steps[player] < step
            )
            for player in player_ids
        }

        # Once a host has completed, all later hosted items are considered
        # released and therefore no longer represent player workload.
        effective_checks_by_player = {
            player: (
                0 if completed_before[player] else raw_checks_by_player[player]
            )
            for player in player_ids
        }

        unfinished_players = [
            player for player in player_ids if not completed_before[player]
        ]
        active_unfinished = [
            player
            for player in unfinished_players
            if effective_checks_by_player[player] > 0
        ]
        starved_unfinished = [
            player
            for player in unfinished_players
            if effective_checks_by_player[player] == 0
        ]

        if active_unfinished:
            for player in starved_unfinished:
                player_events[player]["starvation_steps"].append(step)

        dependency_events = []

        for host in active_unfinished:
            waiting_recipients = [
                recipient
                for recipient in starved_unfinished
                if external_items_by_host_and_recipient[host][recipient] > 0
            ]
            if not waiting_recipients:
                continue

            peer_workloads = [
                effective_checks_by_player[player]
                for player in active_unfinished
                if player != host and effective_checks_by_player[player] > 0
            ]
            active_peer_median = _median(peer_workloads)

            if active_peer_median is None:
                workload_ratio = None
            elif active_peer_median == 0:
                workload_ratio = None
            else:
                workload_ratio = round(
                    effective_checks_by_player[host] / active_peer_median, 3
                )

            external_for_waiting = sum(
                external_items_by_host_and_recipient[host][recipient]
                for recipient in waiting_recipients
            )

            event = {
                "step": step,
                "host": host,
                "host_sendable_checks": effective_checks_by_player[host],
                "active_peer_median_sendable_checks": active_peer_median,
                "workload_ratio_to_active_peer_median": workload_ratio,
                "waiting_players": waiting_recipients,
                "waiting_player_count": len(waiting_recipients),
                "external_progression_for_waiting_players": external_for_waiting,
            }
            dependency_events.append(event)
            player_events[host]["dependency_events"].append(event)

        completing_players = [
            player
            for player in player_ids
            if completion_steps[player] is not None
            and completion_steps[player] == step
        ]

        release_events = []
        for player in completing_players:
            payload = release_payloads[player]
            peer_workloads = [
                effective_checks_by_player[peer]
                for peer in active_unfinished
                if peer != player and effective_checks_by_player[peer] > 0
            ]
            peer_median = _median(peer_workloads)

            if peer_median is None or peer_median == 0:
                release_ratio = None
            else:
                release_ratio = round(payload["released_checks"] / peer_median, 3)

            release_events.append({
                "player": player,
                **payload,
                "release_checks_ratio_to_active_peer_median": release_ratio,
            })

        rows.append({
            "step": step,
            "raw_checks_by_player": {
                str(k): v for k, v in raw_checks_by_player.items()
            },
            "effective_checks_by_player": {
                str(k): v for k, v in effective_checks_by_player.items()
            },
            "completed_before_step": {
                str(k): v for k, v in completed_before.items()
            },
            "active_unfinished_players": active_unfinished,
            "check_starved_unfinished_players": starved_unfinished,
            "dependency_events": dependency_events,
            "completion_release_events": release_events,
        })

    valid_completion_steps = [
        step for step in completion_steps.values() if step is not None
    ]
    group_last_completion = max(valid_completion_steps) if valid_completion_steps else None

    players = {}
    for player in player_ids:
        completion_step = completion_steps[player]

        if completion_step is None or group_last_completion is None:
            completion_position = None
            peers_still_active_fraction = None
        else:
            completion_position = (
                0.0
                if group_last_completion <= 0
                else round(max(completion_step, 0) / group_last_completion, 3)
            )
            peers = [other for other in player_ids if other != player]
            still_active = sum(
                1 for other in peers
                if completion_steps[other] is None
                or completion_steps[other] > completion_step
            )
            peers_still_active_fraction = (
                round(still_active / len(peers), 3) if peers else 0.0
            )

        starvation_steps = player_events[player]["starvation_steps"]

        if completion_step is None:
            eligible_steps = total_steps
        else:
            eligible_steps = max(completion_step + 1, 0)

        longest_starvation = 0
        current = 0
        previous = None
        for step in starvation_steps:
            if previous is not None and step == previous + 1:
                current += 1
            else:
                current = 1
            longest_starvation = max(longest_starvation, current)
            previous = step

        release_payload = release_payloads[player]

        completion_peer_workloads = []
        if completion_step is not None:
            sphere = next(
                (row for row in rows if row["step"] == completion_step),
                None,
            )
            if sphere is not None:
                completion_peer_workloads = [
                    value
                    for peer, value in (
                        (int(k), v)
                        for k, v in sphere["effective_checks_by_player"].items()
                    )
                    if peer != player and value > 0
                ]

        completion_peer_median = _median(completion_peer_workloads)
        if completion_peer_median is None or completion_peer_median == 0:
            release_ratio = None
        else:
            release_ratio = round(
                release_payload["released_checks"] / completion_peer_median, 3
            )

        dependency_events = player_events[player]["dependency_events"]

        players[str(player)] = {
            "progression_bottleneck": {
                # These are dependency events with group-relative workload
                # measurements. v0.9 deliberately does not impose a universal
                # GOOD/BAD threshold.
                "event_count": len(dependency_events),
                "events": dependency_events,
            },
            "early_completion": {
                "completion_step": completion_step,
                "completion_position": completion_position,
                "peers_still_active_fraction": peers_still_active_fraction,
                "completion_detection": completion_detection[player],
            },
            "check_starvation": {
                "starvation_step_count": len(starvation_steps),
                "starvation_steps": starvation_steps,
                "eligible_steps_before_completion": eligible_steps,
                "starvation_fraction_before_completion": (
                    round(len(starvation_steps) / eligible_steps, 3)
                    if eligible_steps > 0 else 0.0
                ),
                "longest_starvation_streak": longest_starvation,
            },
            "early_release": {
                **release_payload,
                "release_checks_ratio_to_active_peer_median": release_ratio,
            },
        }

    return {
        "completion_detection": {
            str(k): v for k, v in completion_detection.items()
        },
        "completion_steps": {str(k): v for k, v in completion_steps.items()},
        "group_last_completion_step": group_last_completion,
        "release_on_goal_completion": True,
        "steps": rows,
        "players": players,
    }

def main() -> int:
    args = parse_args()
    ap_root = args.archipelago.resolve()

    # Make Archipelago importable before importing any of its modules.
    sys.path.insert(0, str(ap_root))

    # Keep stdout machine-readable. Archipelago logging goes to stderr.
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

    import Generate
    import Main
    import Utils

    from apbalance.analysis import analyze_single_seed

    generate_args = Generate.mystery_argparse([
        "--player_files_path", str(args.players.resolve()),
        "--multi", str(args.multi),
        "--skip_output",
        "--spoiler", "0",
    ] + (["--seed", str(args.seed)] if args.seed is not None else []))

    rolled_args, seed = Generate.main(generate_args)
    multiworld = Main.main(rolled_args, seed)

    if args.group:
        raw_spheres = list(multiworld.get_spheres())
        logical_spheres, logical_unreachable = serialize_spheres(raw_spheres)
        completion_steps, completion_detection = completion_steps_from_spheres(
            multiworld, raw_spheres, logical_spheres
        )

        players = []
        for player in range(1, multiworld.players + 1):
            all_locations = list(multiworld.get_locations(player))
            filled_locations = list(multiworld.get_filled_locations(player))
            sendable_locations = [loc for loc in filled_locations if is_sendable(loc)]

            world = multiworld.worlds[player]
            world_version = getattr(world, "world_version", None)
            if hasattr(world_version, "as_simple_string"):
                world_version = world_version.as_simple_string()
            elif world_version is not None:
                world_version = str(world_version)

            players.append({
                "id": player,
                "name": multiworld.get_player_name(player),
                "game": multiworld.game[player],
                "world_version": world_version,
                "world": {
                    "locations_total": len(all_locations),
                    "locations_filled": len(filled_locations),
                    "locations_sendable": len(sendable_locations),
                    "progression_items": progression_count(filled_locations),
                },
            })

        result = {
            "schema_version": 1,
            "analyzer_version": "0.9.0",
            "archipelago_version": getattr(Utils, "__version__", None),
            "seed": seed,
            "seed_name": multiworld.seed_name,
            "players": players,
            "logical_spheres": {
                "count": len(logical_spheres),
                "unreachable_locations": logical_unreachable,
            },
            "timeline_analysis": timeline_analysis(
                multiworld,
                logical_spheres,
                completion_steps,
                completion_detection,
            ),
        }
    else:
        player = 1
        all_locations = list(multiworld.get_locations(player))
        filled_locations = list(multiworld.get_filled_locations(player))
        sendable_locations = [loc for loc in filled_locations if is_sendable(loc)]

        logical_spheres, logical_unreachable = serialize_spheres(
            multiworld.get_spheres()
        )
        sendable_spheres, sendable_unreachable = serialize_spheres(
            multiworld.get_sendable_spheres()
        )

        world = multiworld.worlds[player]
        world_version = getattr(world, "world_version", None)
        if hasattr(world_version, "as_simple_string"):
            world_version = world_version.as_simple_string()
        elif world_version is not None:
            world_version = str(world_version)

        manifest = getattr(world, "manifest", None) or {}

        single_seed_analysis = analyze_single_seed(logical_spheres)

        result = {
            "schema_version": 1,
            "analyzer_version": "0.9.0",
            "archipelago_version": getattr(Utils, "__version__", None),
            "seed": seed,
            "seed_name": multiworld.seed_name,
            "game": multiworld.game[player],
            "world_version": world_version,
            "world_manifest": manifest,
            "player": {
                "id": player,
                "name": multiworld.get_player_name(player),
            },
            "world": {
                "locations_total": len(all_locations),
                "locations_filled": len(filled_locations),
                "locations_sendable": len(sendable_locations),
                "progression_items": progression_count(filled_locations),
                "precollected_items": [
                    item.name for item in multiworld.precollected_items[player]
                ],
            },
            "logical_spheres": {
                "count": len(logical_spheres),
                "unreachable_locations": logical_unreachable,
                "spheres": logical_spheres,
            },
            "analysis": single_seed_analysis,
            "sendable_spheres": {
                "count": len(sendable_spheres),
                "unreachable_locations": sendable_unreachable,
                "spheres": sendable_spheres,
            },
        }

    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
