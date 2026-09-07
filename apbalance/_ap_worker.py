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

def timeline_analysis(multiworld, logical_spheres, completion_steps, completion_detection) -> dict:
    player_ids = list(range(1, multiworld.players + 1))
    total_steps = len(logical_spheres)

    rows = []
    player_events = {
        player: {
            "pressure": [],
            "idle_steps": [],
        }
        for player in player_ids
    }

    for sphere in logical_spheres:
        step = sphere["index"]
        checks_by_player = {player: 0 for player in player_ids}
        external_items_by_host_and_recipient = {
            player: {recipient: 0 for recipient in player_ids}
            for player in player_ids
        }

        for location in sphere["locations"]:
            if not location["sendable"]:
                continue

            host = int(location["player"])
            checks_by_player[host] += 1

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

        unfinished_players = [
            player for player in player_ids if not completed_before[player]
        ]
        active_unfinished = [
            player
            for player in unfinished_players
            if checks_by_player[player] > 0
        ]
        idle_unfinished = [
            player
            for player in unfinished_players
            if checks_by_player[player] == 0
        ]

        # An idle condition only counts while another unfinished player actually
        # has logically available sendable work.
        if active_unfinished:
            for player in idle_unfinished:
                player_events[player]["idle_steps"].append(step)

        pressure_events = []
        for host in active_unfinished:
            waiting_recipients = [
                recipient
                for recipient in idle_unfinished
                if external_items_by_host_and_recipient[host][recipient] > 0
            ]
            if not waiting_recipients:
                continue

            external_for_waiting = sum(
                external_items_by_host_and_recipient[host][recipient]
                for recipient in waiting_recipients
            )

            event = {
                "step": step,
                "host": host,
                "host_sendable_checks": checks_by_player[host],
                "waiting_players": waiting_recipients,
                "waiting_player_count": len(waiting_recipients),
                "external_progression_for_waiting_players": external_for_waiting,
            }
            pressure_events.append(event)
            player_events[host]["pressure"].append(event)

        rows.append({
            "step": step,
            "checks_by_player": {str(k): v for k, v in checks_by_player.items()},
            "completed_before_step": {str(k): v for k, v in completed_before.items()},
            "active_unfinished_players": active_unfinished,
            "idle_unfinished_players": idle_unfinished,
            "progression_pressure_events": pressure_events,
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

        idle_steps = player_events[player]["idle_steps"]

        # Only count timeline steps through this player's own completion point.
        if completion_step is None:
            eligible_steps = total_steps
        else:
            eligible_steps = max(completion_step + 1, 0)

        longest_idle = 0
        current = 0
        previous = None
        for step in idle_steps:
            if previous is not None and step == previous + 1:
                current += 1
            else:
                current = 1
            longest_idle = max(longest_idle, current)
            previous = step

        players[str(player)] = {
            "progression_pressure": {
                "event_count": len(player_events[player]["pressure"]),
                "events": player_events[player]["pressure"],
            },
            "early_completion": {
                "completion_step": completion_step,
                "completion_position": completion_position,
                "peers_still_active_fraction": peers_still_active_fraction,
                "completion_detection": completion_detection[player],
            },
            "idle": {
                "idle_step_count": len(idle_steps),
                "idle_steps": idle_steps,
                "eligible_steps_before_completion": eligible_steps,
                "idle_fraction_before_completion": (
                    round(len(idle_steps) / eligible_steps, 3)
                    if eligible_steps > 0 else 0.0
                ),
                "longest_idle_streak": longest_idle,
            },
        }

    return {
        "completion_detection": completion_detection[player],
        "completion_steps": {str(k): v for k, v in completion_steps.items()},
        "group_last_completion_step": group_last_completion,
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
            "analyzer_version": "0.8.2",
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
            "analyzer_version": "0.8.2",
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
