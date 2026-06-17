# Repository Location

Generated: 2026-06-16T18:15:16-05:00

## Located Project Root

`/home/xqin5/llmlanguage/ir_mstu_stage2`

This directory contains the Stage-2 and Stage-2.5 implementation assets:

- `run_stage2_experiment.py`
- `scripts/run_stage2_5_experiment.py`
- `configs/stage2_5/`
- `data/stage2_5/`
- `src/stage2_5/`
- `results/stage2_mini/`
- `results/stage2_5_repair/`
- `reports/stage2_5/`

## Git Status

The project directory is not a git repository:

```text
git -C /home/xqin5/llmlanguage/ir_mstu_stage2 status --short
fatal: not a git repository (or any of the parent directories): .git

git -C /home/xqin5/llmlanguage/ir_mstu_stage2 rev-parse HEAD
fatal: not a git repository (or any of the parent directories): .git

find /home/xqin5/llmlanguage -maxdepth 3 -name .git -type d -print
(no output)
```

Because no project git metadata exists locally, the Stage-2.5b run cannot use branch/commit gating for this project tree. This limitation is recorded in the initial environment status and checkpoints. Stage-2.5b will instead use hash manifests for code/config/data artifacts and write only to the new allowed Stage-2.5b directories.

## Existing Result And Report Directories

Legacy/read-only directories that must not be overwritten:

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_mini/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_repair/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/reports/stage2_5/`

Other pre-existing Stage-2 result directories are also treated as read-only unless explicitly used as input for an audit:

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_smoke/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_dryrun2/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_gate_check/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_dryrun/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5_audit/`

General protection rule for this run: all pre-existing `results/stage2*` and `reports/stage2_5*` directories are inputs only. New writes must remain in the Stage-2.5b directories listed below.

Stage-2.5b directories created for this run:

- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5b_repair/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5b_audit/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/results/stage2_5b_validation/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/reports/stage2_5b/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/figures/stage2_5b/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/configs/stage2_5b/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/data/stage2_5b/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/artifacts/stage2_5b/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/scripts/stage2_5b/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/src/stage2_5b/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/tests/stage2_5b/`

Two parent container directories were also created because they did not previously exist:

- `/home/xqin5/llmlanguage/ir_mstu_stage2/artifacts/`
- `/home/xqin5/llmlanguage/ir_mstu_stage2/tests/`

These parent directories are containers only. This run must place content inside their `stage2_5b/` children, not in unrelated non-Stage-2.5b paths.

## tau/tau2 Source

`tau2` imports from:

`/home/xqin5/tau2-bench/src/tau2/__init__.py`

Local tau2 repository:

`/home/xqin5/tau2-bench`

Current tau2 git state:

```text
rev-parse HEAD: ddc66a777e520373975f15d3abec989cfe2ec371
describe: voice-user-sim-v1.0-90-gddc66a7
status --short:
 M src/tau2/data_model/message.py
```

This means the loaded tau2 benchmark is not a clean upstream checkout. Phase 1 must freeze the exact current working tree state and file hashes before any benchmark-dependent experiment.

## Conda Environment

Primary experiment environment identified:

`/home/xqin5/.conda/envs/agentsearch`

Observed Python versions:

```text
base python: Python 3.12.7
agentsearch python: Python 3.12.13
```

`pip show tau2-bench` did not find a package name in either base or `agentsearch`; `agentsearch` imports `tau2` from the local source tree above. `importlib.metadata` lists distributions named `tau2`.

## Model Checkpoints

Stage-2.5 stable model checkpoint paths from config and filesystem:

- Gemma4-31B: `/home/xqin5/hf_p08_models/gemma-4-31B-it`
- gpt-oss-120B: `/home/xqin5/hf_p08_models/gpt-oss-120b`

Both paths exist and contain safetensor checkpoints.

Stage-2.5b will initially keep the third-round-required two-model scope:

- `gemma4_31b`
- `gpt_oss_120b`

## GPU State

Observed via `nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader`:

```text
0, NVIDIA A100 80GB PCIe, 81920 MiB, 74239 MiB, 100 %
1, NVIDIA A100 80GB PCIe, 81920 MiB, 74239 MiB, 0 %
2, NVIDIA A100 80GB PCIe, 81920 MiB, 76335 MiB, 0 %
3, NVIDIA A100 80GB PCIe, 81920 MiB, 14 MiB, 0 %
```

Only GPU 3 was effectively free at the time of this check. Full paired two-model runs require endpoint preflight and may require sequential model serving if only one GPU is available.

## Local Port State

`ss -ltnp` showed a listener on port `8005`, consistent with the Gemma endpoint configured in `configs/stage2_5/models.yaml`. No listener on port `8004` was visible in the captured socket list, so the gpt-oss endpoint likely needs to be started before preflight.

## G0_REPO_LOCATED Status

PASS WITH ENVIRONMENT LIMITATION.

The required project, legacy result directories, tau2 source, model checkpoints, conda environment, and GPU state are located. The limitation is that `/home/xqin5/llmlanguage/ir_mstu_stage2` is not a git repository, so project branch/commit gating must be replaced by explicit hash manifests.
