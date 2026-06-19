# CP_001_repo_location_and_protection

## Goal

Locate the active Stage-2 project, identify benchmark/model/environment assets, protect existing results, and decide whether Gate `G0_REPO_LOCATED` can pass.

## Files Inspected

- `/home/xqin5/llmlanguage/第三轮实验意见`
- `/home/xqin5/llmlanguage/skill.md`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/configs/stage2_5/models.yaml`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/`
- `/home/xqin5/tau2-bench/`
- `/home/xqin5/hf_p08_models/`

## Files Changed

- `reports/stage2_5b/REPOSITORY_LOCATION.md`
- `reports/stage2_5b/INITIAL_GIT_AND_ENVIRONMENT_STATUS.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`
- `reports/stage2_5b/FAILURE_AND_REPAIR_LOG.md`
- `reports/stage2_5b/checkpoints/CP_001_repo_location_and_protection.md`

Directories created under the allowed Stage-2.5b namespace:

- `reports/stage2_5b/`
- `reports/stage2_5b/checkpoints/`
- `reports/stage2_5b/run_blocks/`
- `results/stage2_5b_repair/`
- `results/stage2_5b_audit/`
- `results/stage2_5b_validation/`
- `configs/stage2_5b/`
- `data/stage2_5b/`
- `artifacts/stage2_5b/`
- `figures/stage2_5b/`
- `scripts/stage2_5b/`
- `src/stage2_5b/`
- `tests/stage2_5b/`

The parent container directories `artifacts/` and `tests/` were also created because they did not previously exist. They are recorded as containers for `stage2_5b/` content only.

## Evidence Before Change

Project tree:

```text
/home/xqin5/llmlanguage/ir_mstu_stage2
```

Project git checks:

```text
git status --short: fatal: not a git repository
git branch --show-current: fatal: not a git repository
git rev-parse HEAD: fatal: not a git repository
find /home/xqin5/llmlanguage -maxdepth 3 -name .git -type d -print: no output
```

Active tau2 import:

```text
/home/xqin5/tau2-bench/src/tau2/__init__.py
NO_VERSION
```

tau2 git:

```text
HEAD: ddc66a777e520373975f15d3abec989cfe2ec371
describe: voice-user-sim-v1.0-90-gddc66a7
status: M src/tau2/data_model/message.py
```

Existing result roots protected as read-only:

```text
results/stage2_mini
results/stage2_5_repair
results/stage2_smoke
results/stage2_dryrun2
results/stage2_gate_check
results/stage2_dryrun
results/stage2_5_audit
reports/stage2_5
```

GPU:

```text
0, NVIDIA A100 80GB PCIe, 81920 MiB, 74239 MiB, 100 %
1, NVIDIA A100 80GB PCIe, 81920 MiB, 74239 MiB, 0 %
2, NVIDIA A100 80GB PCIe, 81920 MiB, 76335 MiB, 0 %
3, NVIDIA A100 80GB PCIe, 81920 MiB, 14 MiB, 0 %
```

## Implementation

Created only the Stage-2.5b output/code/test directories authorized by the third-round instruction. Wrote repository and environment status reports. Did not modify legacy result directories.

Because the project directory has no `.git`, no branch was created and no commit was recorded. This is documented as an environment limitation rather than silently ignored.

## Tests Executed

- `git -C /home/xqin5/llmlanguage/ir_mstu_stage2 status --short`
- `git -C /home/xqin5/llmlanguage/ir_mstu_stage2 branch --show-current`
- `git -C /home/xqin5/llmlanguage/ir_mstu_stage2 rev-parse HEAD`
- `find /home/xqin5/llmlanguage -maxdepth 3 -name .git -type d -print`
- `conda env list`
- `conda run -n agentsearch python -V`
- `conda run -n agentsearch python -c "import tau2 ..."`
- `git -C /home/xqin5/tau2-bench rev-parse HEAD`
- `git -C /home/xqin5/tau2-bench status --short`
- `git -C /home/xqin5/tau2-bench describe --tags --always`
- `nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader`
- `find /home/xqin5/llmlanguage/ir_mstu_stage2 -maxdepth 2 -type d -name 'stage2_5b*' -print`

## Test Results

The project root and required assets were located. The project has no git metadata. tau2 is importable from `/home/xqin5/tau2-bench`, but that repository has one modified file. The allowed Stage-2.5b directories exist.

## Artifact Inspection

Artifacts produced:

- `reports/stage2_5b/REPOSITORY_LOCATION.md`
- `reports/stage2_5b/INITIAL_GIT_AND_ENVIRONMENT_STATUS.md`
- `reports/stage2_5b/MASTER_EXECUTION_LEDGER.md`
- `reports/stage2_5b/DECISION_LOG.md`
- `reports/stage2_5b/FAILURE_AND_REPAIR_LOG.md`

No files under the pre-existing `results/stage2*` or `reports/stage2_5/` directories were changed.

## Reviewer Verdict

PASS WITH CONCERNS, then repaired in checkpoint revision.

## Reviewer Concerns

- The initial read-only protection statement named only `results/stage2_mini/` and `results/stage2_5_repair/`, while other pre-existing Stage-2 result directories were present.
- The initial directory-change record omitted that parent containers `artifacts/` and `tests/` were created while creating `artifacts/stage2_5b/` and `tests/stage2_5b/`.

## Resolution

Both concerns were repaired by updating `REPOSITORY_LOCATION.md`, `INITIAL_GIT_AND_ENVIRONMENT_STATUS.md`, and this checkpoint to record the broader read-only scope and parent-container creation.

## Final Gate Decision

PASS WITH ENVIRONMENT LIMITATION for `G0_REPO_LOCATED`.

The gate is scientifically sufficient to continue to Phase 1 only if the limitation is accepted: project-level git commit/branch provenance is unavailable, so Stage-2.5b must rely on frozen SHA256 manifests.

## Next Allowed Step

Phase 1: freeze tau/tau2 benchmark version and snapshot task/policy/tool/evaluator files before any task selection, calibration, or experiment execution.
