# Individual LLM Decisions in Crowd Evacuation

Unity research prototype comparing an individual pedestrian LLM's willingness to assist with an original volunteer-game reference model. The LLM chooses its own willingness; it does not command other pedestrians. The reference formula is a theoretical comparator, not a global evacuation optimum or a human-behavior ground truth.

## Current evidence

The original study collected 840 individual decisions across 28 conditions, all technically valid with zero retries. Payoff-task participation was 345/360. The observed decline from low to high cost was smaller than the adjusted game reference, without identifying lower underlying cost sensitivity. Physical-task participation was 236/240 with layout alone and 63/240 with forecasts.

A later information-control experiment collected 480 new decisions across eight physical settings, three information conditions and two instruction option orders. Participation was 141/160 with layout alone, 116/160 with matched unrelated information and 53/160 with forecasts. Forecast minus control was -39.375 percentage points, but the difference was -60.00 points with participate first and -18.75 with decline first. One control topic and partial option-order counterbalancing leave semantic and presentation limitations.

Both studies use gpt-6-luna at temperature 0.15 and remain separately analysed. These are API willingness choices, not human participants or new Unity evacuation outcomes. Pilot, development and earlier group studies remain separate. No further collection is scheduled.

## Essential project files

- `Assets/`, `Packages/`, and `ProjectSettings/`: Unity implementation and project configuration.
- `tools/`: execution, contract validation and analysis utilities.
- `research/`: retained machine-readable specifications and source-bound evidence required by existing manifests. Some hash-bound protocol/result documents remain in place to preserve verification.
- [English experiment notebook](experiment_records/EXPERIMENT_LOG.md): complete chronological record, including failed, pilot, formal and offline preparation work.
- [Record index](experiment_records/README.md): catalogs and data conventions.
- `experiment_records/data/scenario_formal_v1_20261116/`: current raw P030 replies and reason coding, local only.
- `experiment_records/data/analysis/scenario_formal_v1_20261116/`: sealed cell tables, block contrasts, figures and provenance, local only.
- `experiment_records/study_preparations/information_control_v1_20261120/`: locked information-control design, matching audit and request schedule.
- `experiment_records/data/information_control_v1_20261120/` and its matching analysis folder: new raw replies and analysis, local only.

Open the project with the Unity version in `ProjectSettings/ProjectVersion.txt`. Credentials belong in the ignored `openai-key.local.txt`; use `openai-key.example.txt` as a placeholder. Do not commit credentials.

## Read-only formal verification

From the repository root:

```powershell
python tools/scenario_formal.py verify experiment_records/study_preparations/scenario_formal_v1_20261116_r2/registration.json
```

This command verifies existing artifacts without dispatching API requests. Existing data/source hashes and the original campaign claim must remain intact. Do not rerun the completed formal campaign or pool it with pilot responses.

## Local archive

Optional explanations, Chinese writing drafts, old presentations, superseded data and build artifacts are physically consolidated under `local_archive/20261117_cleanup/`, ignored by Git. See its `PLAN.json`, `MOVES.jsonl` and `VERIFIED.json` for original/destination paths and preservation checks. The original long README is saved as `README.before.md` there.

Directory junctions retain historical data paths required by the English notebook and sealed manifests. They point into the local archive; they are not extra copies. Historical references to individually moved documents can be resolved using the move plan. Writing materials are under `local_archive/20261117_cleanup/original/research/scenario_decisions_v2/poststudy_20261117/`.

The ignored archive is local storage, not a remote backup. The cleanup removed only 25 previously tracked generated files under `tmp/pdfs/` from the Git index while retaining their local contents. No commit, push or history rewrite was performed.

## Current local reporting package

The integrated English main report, Traditional Chinese translation, English presentation and speaker notes are in `report/`, which is ignored by Git. The main report includes both separately analysed studies and ends at References. A separate supplement provides seeds, matching checks and actual prompt examples. Advisor: Sai-Keung Wong. Institutional submission rules and author/department metadata have not been supplied.

Local upload packages are prepared in `report/upload/`: a document submission ZIP and a source-only GitHub ZIP. The source package excludes reports, credentials, raw API responses, runtime exports, local archives, editor settings and build outputs. It includes the English experiment notebook and prospective study records. The repository does not currently provide the full raw dataset, so verification commands require the separately retained local evidence. No public raw-data deposit or upload has been made. Discuss public deposition with the supervisor before adding it.
