# Initial Git And Environment Status

Generated: 2026-06-16T18:15:16-05:00

## Project Git

The Stage-2 project tree has no git repository metadata.

Commands executed:

```text
git -C /home/xqin5/llmlanguage/ir_mstu_stage2 status --short
fatal: not a git repository (or any of the parent directories): .git

git -C /home/xqin5/llmlanguage/ir_mstu_stage2 branch --show-current
fatal: not a git repository (or any of the parent directories): .git

git -C /home/xqin5/llmlanguage/ir_mstu_stage2 rev-parse HEAD
fatal: not a git repository (or any of the parent directories): .git
```

Required branch creation command from the Stage-2.5b instruction cannot be safely executed because there is no local git repository:

```text
git checkout -b stage2_5b-confirmatory-repair
not executed: no project git repository exists
```

Resolution for this environment:

- Do not initialize a new repository or fabricate a commit.
- Do not delete or overwrite existing files.
- Use new Stage-2.5b directories only.
- Freeze code/config/data using SHA256 manifests in Phase 1.
- Record this as an execution limitation in all checkpoint and reproduction reports.

## tau2 Git

The benchmark source tree is a git repository:

```text
repo: /home/xqin5/tau2-bench
HEAD: ddc66a777e520373975f15d3abec989cfe2ec371
describe: voice-user-sim-v1.0-90-gddc66a7
status --short:
 M src/tau2/data_model/message.py
```

The tau2 working tree is dirty. This is scientifically material because the active benchmark runtime imports from this source tree. Phase 1 must snapshot exact files and hashes before task selection or evaluation.

## Conda And Python

```text
base Python: Python 3.12.7
agentsearch Python: Python 3.12.13
agentsearch path: /home/xqin5/.conda/envs/agentsearch
tau2 import path: /home/xqin5/tau2-bench/src/tau2/__init__.py
tau2 __version__: NO_VERSION
```

`pip show tau2-bench` returned `Package(s) not found`; the active package appears to be installed/imported as `tau2` from source.

## Models

Configured and present checkpoint paths:

| Alias | Served ID | Base URL | Checkpoint |
|---|---|---|---|
| `gemma4_31b` | `g4` | `http://127.0.0.1:8005/v1` | `/home/xqin5/hf_p08_models/gemma-4-31B-it` |
| `gpt_oss_120b` | `gpt-oss-120b` | `http://127.0.0.1:8004/v1` | `/home/xqin5/hf_p08_models/gpt-oss-120b` |

Current endpoint status is not yet a Stage-2.5b preflight result. Socket inspection showed a listener on `8005`; `8004` was not visible. Formal adapter/endpoint preflight is reserved for Gate G7.

## GPU

```text
0, NVIDIA A100 80GB PCIe, 81920 MiB, 74239 MiB, 100 %
1, NVIDIA A100 80GB PCIe, 81920 MiB, 74239 MiB, 0 %
2, NVIDIA A100 80GB PCIe, 81920 MiB, 76335 MiB, 0 %
3, NVIDIA A100 80GB PCIe, 81920 MiB, 14 MiB, 0 %
```

GPU 3 was the only free A100 at initial inspection.

## Asset Protection Decision

Existing result directories are treated as read-only:

- `results/stage2_mini/`
- `results/stage2_5_repair/`
- `results/stage2_smoke/`
- `results/stage2_dryrun2/`
- `results/stage2_gate_check/`
- `results/stage2_dryrun/`
- `results/stage2_5_audit/`
- `reports/stage2_5/`

No old result or report files were edited or deleted during Phase 0. New work is isolated to the Stage-2.5b directories required by the third-round instruction. The parent container directories `artifacts/` and `tests/` were created because they did not exist; all content under them must remain inside `artifacts/stage2_5b/` and `tests/stage2_5b/`.
