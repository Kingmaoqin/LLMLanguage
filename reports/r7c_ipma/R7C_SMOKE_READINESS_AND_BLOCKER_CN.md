# R7-C smoke readiness and blocker

- code status: READY_FOR_SMOKE_PREFLIGHT
- full preflight gate: PASS
- planned full cells: 2592
- planned smoke cells: 144
- targeted tests: PASS, 8/8
- live smoke status: BLOCKED_BY_ENDPOINT

## verified code-side fixes

- R7-B/R7-C PASR safety gate is fail-closed for missing/empty/None/NaN/unparseable safety, privacy, policy, endpoint, pairing, and semantic fields.
- R7-B after-fix PASR remains 45/1080 with changed_pairs=0 on complete traces.
- R7-C placebo uses neutral-control per-(model, task) noise floors and uses pooled neutral placebo as the go/no-go decision basis.
- R7-C `CORE_SUPPORTED` go/no-go branch is reachable under low pooled placebo and no semantic/noise/strength caveats.
- R7-C frozen asset expansion now contains 48 endpoint-supported test tasks and 2880 frozen templates.
- R7-C runner plan-only uses R7-C registry, frozen templates, tasks, policies, annotations, and seed states.
- Live runner now writes endpoint readiness to `r7c_endpoint_preflight.json` before failing closed.
- R7-C queue script exists and explicitly uses R7-C assets for smoke/full plus postprocess.
- R7-C full queue is gated on a passed smoke root and refuses full without `R7C_SMOKE_ROOT`.

## machine verification

- `python -m py_compile scripts/r7b_ipma/run_r7b_live.py scripts/r7c_ipma/build_r7c_assets.py scripts/r7c_ipma/preflight_r7c_full_gate.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/r7c_ipma/test_fail_closed_safety_gate.py tests/r7c_ipma/test_placebo_go_nogo.py tests/r7b_ipma/test_r7b_fail_closed.py -q`: PASS, 8 passed
- `python scripts/r7c_ipma/preflight_r7c_full_gate.py --registry data/r7c_ipma/r7c_task_registry.csv --config configs/r7c_ipma/r7c_full.yaml --templates data/r7c_ipma/frozen/r7c_frozen_templates.jsonl`: PASS, 48 tasks, 2592 planned cells, missing_template_cells=0
- `bash scripts/r7c_ipma/queue_r7c_smoke_full.sh smoke plan`: PASS, 144 planned cells, R7-C frozen templates selected
- `bash scripts/r7c_ipma/queue_r7c_smoke_full.sh full plan`: PASS, 2592 planned cells, R7-C frozen templates selected
- `R7C_ALLOW_SMOKE=1 bash scripts/r7c_ipma/queue_r7c_smoke_full.sh smoke`: FAIL_CLOSED_BEFORE_MODEL_CALLS, `gemma4_31b:8005` connection refused
- `python scripts/r7b_ipma/judge_template_semantic_invariance.py --templates data/r7c_ipma/frozen/r7c_frozen_templates.jsonl ...`: PASS, 2880 templates, 0 semantic failures
- `python scripts/r7c_ipma/verify_r7c_smoke_gate.py --smoke-root results/r7c_ipma/smoke/live_20260709_231615 ...`: EXPECTED_FAIL, rejects incomplete smoke evidence
- `R7C_ALLOW_FULL=1 bash scripts/r7c_ipma/queue_r7c_smoke_full.sh full`: EXPECTED_FAIL, refuses without `R7C_SMOKE_ROOT`

## endpoint blocker

R7-C live smoke cannot start because the fixed 3-model roster is not all online:

- `gemma4_31b`: FAIL, `http://127.0.0.1:8005/v1`, `Connection refused`
- `gpt_oss_120b`: OK, `http://127.0.0.1:8192/v1`, served id `gpt-oss`
- `mistral_small_3p2`: OK, `http://127.0.0.1:8007/v1`, served id `mistral-small-3p2`

Machine endpoint table:

- `results/r7c_ipma/smoke/live_endpoint_preflight_latest/r7c_endpoint_preflight.json`
- `results/r7c_ipma/smoke/live_20260709_231615/r7c_endpoint_preflight.json`

## required approval before smoke

To proceed to live smoke, `gemma4_31b` must be started on `:8005` with served id `g4`. Existing project reproduction notes show Gemma4 requires `--max-num-batched-tokens 8192`.

Prepared non-destructive startup script:

- `scripts/r7c_ipma/start_r7c_gemma4_endpoint.sh`

Prepared R7-C queue:

- `scripts/r7c_ipma/queue_r7c_smoke_full.sh`
- smoke command after endpoint readiness: `R7C_ALLOW_SMOKE=1 bash scripts/r7c_ipma/queue_r7c_smoke_full.sh smoke`
- smoke gate after smoke completes: `python scripts/r7c_ipma/verify_r7c_smoke_gate.py --smoke-root <smoke_root>`
- full command after smoke gate and review approval: `R7C_ALLOW_FULL=1 R7C_SMOKE_ROOT=<smoke_root> bash scripts/r7c_ipma/queue_r7c_smoke_full.sh full`

The script:

- does not stop or kill existing processes;
- exits immediately if `:8005` already serves `g4`;
- otherwise starts Gemma4 with vLLM, writes a pid file and log, and waits for `/v1/models`;
- defaults to the freest GPU unless `R7C_GEMMA_GPU` is set.

This action was not executed because starting a persistent GPU service requires explicit user approval.
