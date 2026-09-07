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

    generate_args = Generate.mystery_argparse([
        "--player_files_path", str(args.players.resolve()),
        "--multi", "1",
        "--skip_output",
        "--spoiler", "0",
    ] + (["--seed", str(args.seed)] if args.seed is not None else []))

    rolled_args, seed = Generate.main(generate_args)
    multiworld = Main.main(rolled_args, seed)

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

    result = {
        "schema_version": 1,
        "analyzer_version": "0.1.0",
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
