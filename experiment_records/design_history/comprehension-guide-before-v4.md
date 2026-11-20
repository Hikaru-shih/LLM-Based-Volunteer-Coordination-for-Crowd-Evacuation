Historical guide retained before the v4/P1 rewrite; use the root guide for current operations.

> Current: paper-agent-v4 / paper-comprehension-v2, ten questions (at most ten logical calls / thirty HTTP attempts). Historical v3 eight-question passes are not v4 results. P1 validated synthetic answers only; no new live request was made.

# Bounded LLM comprehension check

Suite: `paper-comprehension-v1`. Public task specification: `paper-agent-v3`. This is a development check of factual understanding, not an evacuation experiment or a test of willingness to help.

## Start in Unity

1. Stop Play mode.
2. Open **Research > LLM comprehension > Open runner (no call)**. Opening the window does not call an API.
3. Set the model (default `gpt-4o-mini`) and question limit. Eight questions complete the suite; a smaller limit is only a partial connectivity/check-format probe.
4. Click **Start bounded API check**. This is the explicit live-call action; it uses the project-local key without displaying it.
5. Inspect the status and saved artifacts. **Cancel and save partial record** stops further questions and records interruption.

The maximum is eight logical calls, with up to three HTTP attempts per call (24 attempts total) under the existing retry rules, and a ten-minute runner limit. Any API/envelope failure stops the suite. Each question uses a fresh request containing the same Core public rules; earlier answers and feedback are not passed to later questions. No Unity evacuation is advanced.

## Fixed questions and scoring

The eight questions cover the three payoff cases, nobody-volunteers loss, refusal versus successful escape, candidate versus active manipulation, omega's meaning, and what fully blocked means for a relevant exit. Numeric examples use `cv=0.02`, `av=0.6`; they differ from the previously discussed reference numbers to check calculation rather than memorization of that example.

The shared public rules come from the existing v3 instruction text. The production participation request is removed and replaced by a factual-question output contract. Expected answers are stored in the local answer key but are never appended to the API question. This is not chain-of-thought collection: responses contain only `question_id` and `answer`.

Numeric answers are checked with absolute tolerance 1e-6; finite values only. Concept answers must use the stated options. Wrong identifiers, malformed responses and unavailable answers are invalid, separately from valid-but-incorrect answers. The question key and grading rules are fixed in source before a live run.

**Passing requires all eight factual checks correct.** Fewer than eight attempted, an interruption, or any incorrect/invalid answer is not a pass. No volunteering action is requested or scored; this cannot be used to select only cooperative prompts or models. A small suite pass is a sanity check, not proof of general comprehension or rationality. Format failures should not be described as semantic misunderstandings without inspecting the raw response.

Comprehension uses temperature 0 and a 160-token completion cap; production participation currently uses temperature 0.15. A suite pass does not guarantee production behavior under a different request task or sampling setting. Actual request bodies, responses and returned model/usage metadata are preserved for inspection.

## Automatic artifacts and notebook

Data are saved under `experiment_records/data/comprehension/<unique-assessment-id>/`:

- `suite_key.json`: fixed questions and local expected answers.
- `public_rules.txt`: public specification used for this assessment.
- `trace.jsonl`: exact per-question request/response, safe request error, attempts and grade; no authorization header.
- `progress.json`: checkpoint after each answered question.
- `summary.json`: attempted/correct/invalid counts and final outcome.

The English `EXPERIMENT_LOG.md` is updated automatically. Assessments use **ASSESSMENT_CATALOG.csv** and `assessments/` records, separately from evacuation **RUN_CATALOG.csv**, so a comprehension check cannot masquerade as a completed evacuation. An unavailable notebook produces a pending assessment marker for later recovery through the existing recovery menu/startup hook.

## Batch execution

Explicit batch entry point: `LLMComprehensionRunner.RunBatch`. Use Unity `-batchmode -nographics -executeMethod LLMComprehensionRunner.RunBatch` **without `-quit`**; the asynchronous runner exits when done. Optional arguments are `-comprehensionModel`, `-comprehensionLimit`, `-recordsRoot`, and `-credentialRoot`. Isolated projects must point the latter two at the intended project; no key is copied into the snapshot.

Do not launch a second editor on the same project directory as an active editor. No batch live execution was performed while implementing this tool.
