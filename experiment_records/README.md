# Experiment and Validation Records

This is the central English-language notebook and data index for this project. It separates historical work, development diagnostics, functional comparisons, and formal research. **Completed campaigns are recorded separately: P028 group evacuation, P030 individual scenario decisions and P031 information control; earlier interrupted and pilot data remain distinct.**

Start with [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md). Individual development and functional runs are indexed in [RUN_CATALOG.csv](RUN_CATALOG.csv). The relocation manifest records original and current paths; individual moved files have SHA-256 checks, while complete historical directories were renamed on the same volume.

## Directory organization by purpose

| Location | Purpose |
|---|---|
| `data/historical_archive/2026-11-09_before_redesign/` | Previously archived raw datasets, plots, and validation evidence from older system snapshots; original directory structure retained |
| `data/development/api_connectivity_and_credentials/` | Missing-credential, HTTP 401, and HTTP 429 diagnostics |
| `data/development/recruitment_trigger_random_room/` | Random-room runs with no API decisions; used to investigate recruitment triggers |
| `data/development/llm_decision_behavior_random_room/` | Successful API calls under the earlier non-reference settings; used to investigate universal refusal |
| `data/functional_comparison/blocked_exit_llm/` | Bounded live LLM functional test with reference physical parameters |
| `data/functional_comparison/blocked_exit_game_theory/` | Original game-theory policy on the same initial blocked-exit fixture |
| `data/functional_comparison/blocked_exit_no_volunteers/` | NoVolunteers control on that same fixture |
| `data/validation/` | Local Unity launcher/contract/flow/menu logs and wiring-check output |

Raw data are kept locally and ignored by Git. The notebook, catalog, verification summaries, and relocation manifests can be versioned. Credentials are not included by the organizer.

## Reading the catalog

- `stop_step` is when execution stopped. It is **not** T100 unless termination is `completed`.
- Empty `t100_steps` means full evacuation was not observed. A request-limit failure is not a physical timeout.
- `willing_decisions` counts positive agent–obstacle decision events, not distinct volunteers.
- `activations` counts transitions into actual obstacle handling. `settled` counts completed obstacle placements.
- `api_logical_calls` counts policy requests; retries can make the number of HTTP attempts larger.
- `initial_state_sha256` hashes normalized step-zero pedestrian and obstacle rows. Matching hashes support identical initialization, not identical subsequent trajectories.
- Recorded filenames use UTC for the current test runners. Notebook dates use Asia/Taipei (UTC+08:00). Thus `20261109_16xxxx` belongs to November 10 locally.

## Future records

Record the question, fixed settings, strategy changes, seed, stopping rules, actual outcome, limitations, and data path for every new test. Preserve failed runs and raw responses. Do not mix old versions, replay validation, calibration, or functional checks with final-test replicates.

Unity currently stages newly exported runs in `Assets/data/`; this folder was emptied by the current archival. `tools/organize_test_records.py` moves existing staging and known diagnostic artifacts into purpose-specific directories without running a simulation or calling an API. Existing destination collisions are rejected; inspect and version new validation logs rather than overwriting archived evidence.

## Windows path-length note

The historical archive contains 5,058 paths at or above the legacy Windows 260-character threshold. Extended-length (`\\?\`) inventory verified that all 31,366 historical files and their total bytes were preserved. Use the organizer's extended-path helper or a long-path-aware tool when enumerating this archive; a plain recursive listing may silently undercount it.

## In-progress staging

At collection time, batch `889d142d`, run 013 had an unexported trace in `Assets/data/` but no completed run configuration/global record. It was deliberately left in staging because it might still be written by the interactive Unity session. It is not included among the 22 cataloged completed-or-terminated exports. Stop Play before archiving this trace; do not count it as a finished replicate.

## Automatic recording (enabled)

SimulationManager now records each exported run automatically. In the Unity Editor the default root is this `experiment_records` directory; built players use `Application.persistentDataPath/experiment_records`. New default exports go directly to short-ID folders under `data/auto/`, grouped by purpose. The optional Inspector `experimentPurpose` supplies the question being tested; if blank, a factual default identifies phase, policy and scenario without inventing an objective.

After export, the English notebook receives a generated entry, RUN_CATALOG.csv receives an idempotent row, and `entries/` retains a machine-readable record. Existing handwritten observations are preserved above the generated section. Entries describe outcomes, not unverified causal explanations. Full configurations and raw artifacts are linked; runtime catalog rows leave the optional initialization hash blank rather than manufacturing one.

Completed, timeout, invalid and controlled interruption/reset/scene-exit records are included. A hard process crash or an export failure cannot guarantee a final entry. If notebook publication fails after raw export, a `_notebook_pending.json` marker preserves the record. Pending default-folder entries are retried on the next Editor initialization or via Research > Experiment notebook > Retry pending entries (no run). No network or LLM is used to write the notebook.

Explicit custom export folders are retained as recovery/source copies while a verified per-run copy is archived centrally. Unit/contract validation fixtures disable production recording; the bounded functional runners explicitly enable it. This prevents synthetic software checks from being presented as new research executions.

## P030 formal scenario decisions (2026-11-16)

840 fresh live choices,28 conditions x30;840 reasons assistant-reviewed. Raw: [formal data](data/scenario_formal_v1_20261116/). Analysis: [formal tables and provenance](data/analysis/scenario_formal_v1_20261116/). [Chinese results](../research/scenario_decisions_v2/FORMAL_RESULTS.zh-TW.md). P029 pilot,physical-development calibration and P028 group runs are excluded from P030 estimates.

## P031 information control (2026-11-20)

480 fresh live choices, eight physical settings × three information conditions × two instruction orders × ten replies. See [locked design](study_preparations/information_control_v1_20261120/design.json) and [matching audit](study_preparations/information_control_v1_20261120/PROMPT_MATCH_AUDIT.json). Participation counts are141/160 layout,116/160 matched unrelated information and53/160 forecast. The forecast-control difference depends strongly on instruction order. Raw replies and analysis remain in the ignored `data/` directory. Neither original actions nor earlier reason labels were changed. New reasons remain uncoded. The integrated main report and appendix are local deliverables under `report/`, excluded from the source upload package. The source repository alone does not contain the raw evidence needed for full verification.
