# AP Balance Analyzer

Archipelago multiworld pacing and outlier analysis.

## Primary goal

Analyze a group of player YAMLs together and identify recurring structural pacing risks.

v0.9.2 reports four separate conditions:

- progression bottleneck
- early completion
- check starvation
- early release

These are descriptive group-relative measurements, not difficulty ratings.

## Assumptions

Players are assumed to be capable of completing logically available checks as they become accessible, with comparable efficiency and without substantial skill, execution, routing, knowledge, break, or communication delays. Actual play time may differ significantly between games and players.

Check starvation means an unfinished player has no sendable Archipelago checks in the current logical progression step while another unfinished player does. It does not necessarily mean the player has no meaningful in-game activity.

When a player completes their configured goal, all remaining items hosted in that player's world are assumed to be released immediately. Post-goal locations therefore no longer contribute player workload or bottleneck risk.

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
  --apworld "C:\apworlds\another.apworld" `
  --samples 100 `
  --output group-analysis.json
```

## Progression bottleneck

A dependency event occurs when an unfinished player has no sendable checks and progression for that player is hosted in another unfinished player's current workload. A dependency event becomes a bottleneck candidate only when that host is the unique highest-workload active player in the same progression step.

Each event reports:

- host sendable checks
- median sendable checks among other active peers
- host workload ratio to that peer median
- waiting players
- external progression for those waiting players

v0.9.2 does not impose a universal workload-ratio threshold. Raw dependency events remain in the output for auditability.

Bottleneck ranking uses `bottleneck_exposure_index = bottleneck_candidate_seed_frequency × median_candidate_workload_ratio_to_active_peer_median`, so persistent severe candidates rank above rare severe candidates.

## Early completion

Reports goal-completion position relative to the last completing player and the fraction of peers still active at completion.

## Check starvation

Reports:

- seeds with starvation
- starvation steps
- starvation fraction before completion
- longest starvation streak

## Early release

At goal completion, later hosted checks are definitely released, while checks in the completion sphere have unknown within-sphere order. Release impact is therefore reported as minimum, expected, and maximum. Expected assumes a neutral 50% of completion-sphere hosted checks remain.

Reports:

- remaining checks released
- remaining progression items released
- external progression released
- recipient players affected
- release size relative to active-peer workload at completion

Early completion and early release remain separate conditions.

## Completion detection

Completion is evaluated using each world's Archipelago completion condition while replaying logical-sphere progression. Fallbacks are explicitly labeled as:

- `last_progression_event_proxy`
- `last_sendable_check_proxy`
- `completion_unavailable`

## Secondary commands

```powershell
apbalance inspect Player.yaml --archipelago "C:\path\to\Archipelago"
apbalance analyze Player.yaml --archipelago "C:\path\to\Archipelago" --samples 100
apbalance config Player.yaml --output config.json
```

Progression Balancing mitigation analysis is not yet implemented.
