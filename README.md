# AP Balance Analyzer

Archipelago multiworld outlier analysis.

## Primary goal

Analyze a group of player YAMLs together and detect three pacing problems:

- progression overload: one player has substantial logical workload while idle players are waiting on progression hosted in that world
- early completion: one player completes substantially before peers
- idle time: one player has no logically available sendable checks while unfinished peers are still playing

## Assumption

Players are assumed to be capable of completing logically available checks as they become accessible, with comparable efficiency and without substantial skill, execution, routing, knowledge, break, or communication delays. Actual play time may differ significantly between games and players.

## Group analysis

```powershell
apbalance group ".\Players" `
  --archipelago "C:\path\to\Archipelago" `
  --samples 100 `
  --output group-analysis.json
```

Custom worlds can be supplied more than once:

```powershell
apbalance group ".\Players" `
  --archipelago "C:\path\to\Archipelago" `
  --apworld "C:\apworlds\plateup.apworld" `
  --samples 100 `
  --output group-analysis.json
```

## Group output

Per player:

- progression-pressure event frequency
- checks during progression-pressure events
- waiting-player count
- external progression for waiting players
- completion position relative to the last completing player
- fraction of peers still active at completion
- idle-step frequency
- idle fraction before completion
- longest idle streak

Separate rankings are emitted for progression pressure, early completion, and idle time.

Completion is evaluated using each world's Archipelago completion condition while replaying the same logical-sphere progression used by Archipelago. A condition that is already true at the initial state is rejected for timeline use. Fallbacks are explicitly labeled as `last_progression_event_proxy`, `last_sendable_check_proxy`, or `completion_unavailable`.

## Secondary commands

```powershell
apbalance inspect Player.yaml --archipelago "C:\path\to\Archipelago"
apbalance analyze Player.yaml --archipelago "C:\path\to\Archipelago" --samples 100
apbalance config Player.yaml --output config.json
```

## Status

Player skill and real-world check duration are not modeled. Progression Balancing mitigation analysis is not yet implemented.
