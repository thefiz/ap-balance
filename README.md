# AP Balance Analyzer

Archipelago YAML analysis tool.

## Features

- Single YAML inspection
- Optional custom `.apworld`
- Local Archipelago generation
- Logical/sendable sphere extraction
- Single-seed analysis
- Multi-seed simulation and aggregate statistics
- Mid-run thin-sphere and consecutive-thin detection
- Post-opening wide-sphere detection
- Sendable progression dilution

## Requirements

- Python 3.11+
- Local Archipelago checkout/install
- Archipelago Python dependencies

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install -r "C:\path\to\Archipelago\requirements.txt"
```

## Usage

Single seed:

```powershell
apbalance inspect Player.yaml --archipelago "C:\path\to\Archipelago"
```

Multi-seed simulation:

```powershell
apbalance analyze Player.yaml `
  --archipelago "C:\path\to\Archipelago" `
  --samples 100 `
  --output analysis.json
```

Custom world:

```powershell
apbalance analyze Player.yaml `
  --archipelago "C:\path\to\Archipelago" `
  --apworld ExampleGame.apworld `
  --samples 100
```

## Roadmap

- Progression balancing recommendations
- Same-game baselines
- Cross-game normalization
- Group multiworld analysis
