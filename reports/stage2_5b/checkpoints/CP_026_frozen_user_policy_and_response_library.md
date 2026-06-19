# Checkpoint CP-026

## Goal

Create frozen task-user policy and deterministic response-library data before replacing the
active controlled user.

## Existing Implementation

Task policies were Python constants for six tasks, while all other candidate policies were
generated at runtime from tau2 user scenarios. Clean responses were stored directly inside the
policy object.

## Problem Evidence

Runtime policy generation is not a frozen experimental treatment and makes provenance depend
on transformation code and benchmark prose at execution time. It also prevents a clean
separation between task decisions and linguistic rendering.

## Minimal Change Plan

Add a frozen 16-task retail calibration panel plus policies for the existing airline and legacy
validation tasks, add a shared response library, and implement independent loaders/renderers.
Do not switch the runner in this checkpoint.

## Files Changed

- `data/stage2_5b/task_user_policies.yaml`
- `data/stage2_5b/user_response_library.yaml`
- `src/stage2_5b/user_policy.py`
- `src/stage2_5b/response_library.py`
- `tests/stage2_5b/test_response_library_schema.py`

## Git Diff Summary

- Added 16 frozen calibration policies.
- Added explicit user facts, preferences, payment constraints, confirmation details, and
  decisions.
- Added a declarative request-state map.
- Added deterministic template selection using
  `hash(task_id, seed, speech_act, state_id) % template_count`.
- Removed hidden task-instruction/style/tool names from the frozen user data.

## Tests

```text
conda run -n agentsearch python -m unittest \
  tests.stage2_5b.test_response_library_schema

conda run -n agentsearch python -m unittest discover -s tests/stage2_5b
```

## Results

- Schema/determinism tests: PASS, 4/4
- Full Stage-2.5b suite: PASS, 68/68
- YAML parse, compile, diff, and leakage-pattern scan: PASS

## Artifact Inspection

Rendered every core speech act for every frozen task. All produced a non-empty response ID and
clean text. Repeated rendering for the same task/seed/state/speech act was identical.

## Dead-Code Check

The old Python policy and runtime generic-policy generator remain active only until the next
checkpoint switches `ControlledUser`.

## Reviewer Findings

Development-time extraction exposed benchmark prose containing hidden style/process
instructions and second-person remnants. Those strings were not copied verbatim; policies were
manually normalized to agent-facing facts and decisions before freezing.

## Gate

PASS.

## Rework

Removed all detected hidden instruction, tool-name, and social-style phrases from frozen policy
data before the full test run.
