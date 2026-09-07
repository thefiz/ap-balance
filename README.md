# AP Balance Analyzer

Prototype v0.1 for analyzing Archipelago player YAMLs by generating them through a local Archipelago installation and inspecting the resulting `MultiWorld`.

## Current milestone

v0.1 intentionally does only the foundation:

- accept one player YAML
- accept a path to a local Archipelago source/install tree
- optionally stage one custom `.apworld`
- generate locally with Archipelago's normal generator
- use `skip_output` so patch/ROM output is not generated
- inspect the returned `MultiWorld`
- record:
  - game
  - player
  - location count
  - filled/sendable location count
  - progression item count
  - logical sphere count
  - sendable sphere count
  - per-sphere check counts
  - per-sphere progression counts
  - unreachable locations, when detectable
- output JSON

No "difficulty" or "fit" score exists yet. We want to validate the underlying measurements first.

## Why this architecture

The analyzer runs the real Archipelago generator rather than reimplementing world logic. This lets core and custom worlds use their own regions, rules, items and option implementations.

Generation is performed with Archipelago's `skip_output` path. This still creates regions, items, rules, fills the world and performs progression balancing, but returns the completed `MultiWorld` before output generation.

## Installation

Create a virtual environment for AP Balance itself:

```bash
python -m venv .venv
```

Activate it and install:

```bash
pip install -e .
```

The Archipelago installation must separately have the Python dependencies required to run its source tree.

## Usage

Core world:

```bash
apbalance inspect Player.yaml --archipelago /path/to/Archipelago
```

With a custom APWorld:

```bash
apbalance inspect Player.yaml \
  --archipelago /path/to/Archipelago \
  --apworld ExampleGame.apworld
```

Choose a deterministic seed:

```bash
apbalance inspect Player.yaml \
  --archipelago /path/to/Archipelago \
  --seed 123456
```

Write JSON to a file:

```bash
apbalance inspect Player.yaml \
  --archipelago /path/to/Archipelago \
  --output result.json
```

## Important custom APWorld behavior

For this first prototype, a supplied `.apworld` is temporarily copied into the selected Archipelago installation's `custom_worlds` directory for the duration of the child generation process and then removed.

The tool refuses to overwrite an existing file with the same name.

A later milestone should replace this with a fully isolated Archipelago analysis environment.

Custom APWorlds are executable Python. Only analyze APWorlds you would otherwise trust enough to run with Archipelago.

## JSON shape

Example:

```json
{
  "schema_version": 1,
  "seed": 123456,
  "game": "Example Game",
  "player": {
    "id": 1,
    "name": "Player"
  },
  "world": {
    "locations_total": 120,
    "locations_filled": 120,
    "locations_sendable": 118,
    "progression_items": 32
  },
  "logical_spheres": {
    "count": 12,
    "spheres": [
      {
        "index": 0,
        "checks": 14,
        "progression_items": 4
      }
    ]
  },
  "sendable_spheres": {
    "count": 12,
    "spheres": []
  }
}
```

## Next milestone

Once this works against several real worlds, v0.2 will add repeated generation and aggregate statistics:

- sphere width distributions
- early cumulative workload
- thin-sphere detection
- wide-sphere detection
- progression dilution
- variance
