# AP Balance Analyzer

Archipelago YAML analysis tool.

## Current features

- Single YAML inspection
- Optional custom `.apworld`
- Local Archipelago generation
- Logical and sendable sphere extraction
- World/location/progression counts
- Single-seed sphere analysis:
  - sphere width statistics
  - early cumulative workload
  - thin-sphere detection
  - wide-sphere detection
  - progression dilution

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

```powershell
apbalance inspect Player.yaml --archipelago "C:\path\to\Archipelago"
```

Custom world:

```powershell
apbalance inspect Player.yaml `
  --archipelago "C:\path\to\Archipelago" `
  --apworld ExampleGame.apworld
```

Deterministic seed and file output:

```powershell
apbalance inspect Player.yaml `
  --archipelago "C:\path\to\Archipelago" `
  --seed 123456 `
  --output result.json
```

## Roadmap

- Multi-seed simulation
- Variance and percentile reporting
- Progression balancing recommendations
- Same-game baselines
- Group multiworld analysis
