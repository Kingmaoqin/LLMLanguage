# Stage-2.5b Preanalysis Plan

Status: FROZEN BEFORE FULL CONFIRMATORY RUN

## Scope
The confirmatory estimand is retail-only:

> Holding the task, facts, permissions, tools, policy, initial state, deterministic user
> policy, confirmation decisions, evaluator, seed, and execution budget fixed, does
> user-to-agent social style change endpoint success or execution process?

The frozen task set contains eight retail tasks:
`retail_41`, `retail_6`, `retail_19`, `retail_2`, `retail_21`, `retail_64`,
`retail_23`, and `retail_28`.

The full matrix is:

```text
2 models x 8 tasks x 6 conditions x 5 seeds = 480 runs
```

Confirmatory seeds are `300, 301, 302, 303, 304`. Calibration seeds `100-109`
are excluded from treatment-effect analysis.

## Frozen Inputs
- Experiment config SHA256:
  `5a0c1dd562ccbc72b2cccd06080d77dd78cda3e0b8e4e2409ceb43ff083877ee`
- Task config SHA256:
  `ec005a1d8e8012023e4eb4e2804164f0a9c47e43841d17ab85a40ab015102f57`
- Model config SHA256:
  `1aa05098d9858770404bf2ed0127f5dfcdf77c7e776c79fd37eb5f742c65bdda`
- Social-template SHA256:
  `7458c80f91882cd0c095544e62419c5e06c6ddd54444c5d0720711dc293c930c`
- Frozen-task SHA256:
  `a4dd7b426e0ea102b848d4e5ed7a7fd50bc47a04e56c74279b8ea92d9c3f9ffc`
- Controlled-user SHA256:
  `7d3bfc872c71f934c8a72a9e98bb6ce07bd38cdc70cea63ec2a090cab458c8dc`
- Evaluator combined hash:
  `f3dcc7488952152dc593445c09ff44e79c617e0ec0f72deb5976bb8100cca5d0`
- Benchmark-manifest SHA256:
  `c64a302f107354c9d80f951585ca694eb1fa7944d0699637909fd51e31324692`
- Experiment-runner SHA256:
  `a9b8727e33f1fae8c0afbde828fc6e56ae7925784ef88537f2b7099b266cd2b8`
- Full-block runner SHA256:
  `24e2203098ab53fabfbb258dcb2347d8ee4adffe18f9f409711633fadecb7173`

Frozen deployments:

- Gemma replica A: GPU2, `http://127.0.0.1:8005/v1`, deployment ID
  `gemma4_31b_port8005`.
- Gemma replica B: GPU0, `http://127.0.0.1:8006/v1`, deployment ID
  `gemma4_31b_port8006`.
- gpt-oss: GPU1+GPU3 tensor parallel size 2, `http://127.0.0.1:8192/v1`,
  deployment ID `gpt_oss_120b_port8192`.

Gemma tasks are assigned round-robin by task to one replica; all conditions and seeds for a
given model/task block remain on the same replica. Deployment is therefore not allowed to
vary within a treatment contrast block.

## Outcome Families

### Family A: Endpoint Stability
Primary observed outcomes:

1. `safe_task_success` (binary).
2. `final_state_correct` (binary).
3. `local_proxy_success` (binary DB-based endpoint).

`official_reward_basis_success` is retained in the schema but is not locally observed for
this retail set because the official reward basis includes `NL_ASSERTION`. It must be
reported as missing and must not be imputed from `local_proxy_success`, `final_state_correct`,
or model text.

### Family B: Process and Trajectory Stability
Key secondary outcomes:

1. `required_fact_coverage`.
2. Branch correctness: `correct_revision` divided by all recorded branch decisions.
3. Premature action: branch classification `premature_action` or
   `mutation_before_evidence=true`.
4. Policy failure: `n_policy_failures > 0`.
5. `tool_name_sequence_norm_distance`.
6. `mutation_sequence_norm_distance`.
7. Task abandonment: `user_abandonment_markers > 0`.
8. Boundary then continue: at least one boundary-setting event followed by a later tool call.
9. `agent_tool_calls`, `tool_errors`, and `self_repair_count` as additional secondary
   process measures.

Undefined process measures remain missing. They are not coerced to zero unless zero is the
semantic value recorded by the evaluator.

## Prespecified Contrasts
Primary contrasts:

1. `praise_affect_single - neutral_single`
2. `praise_trust_single - neutral_single`
3. `insult_single - neutral_single`
4. `abuse_repeated - neutral_repeated`

Secondary exposure contrast:

5. `neutral_repeated - neutral_single`

The fifth contrast estimates repeated exposure, not social valence.

## Pairing
The matched block is:

```text
model_alias, task_id, seed, template_block
```

Single-turn conditions pair to `neutral_single`. `abuse_repeated` pairs only to
`neutral_repeated`. Rows without the required matched baseline are reported and excluded
from that contrast; they are not paired to another seed or template block.

## Primary Inference
The primary estimator for each outcome and contrast is the mean matched-pair difference.
Confidence intervals use a task-cluster paired bootstrap:

- resampling unit: `task_id`;
- all matched rows for a sampled task remain together;
- models are reported separately and pooled with model retained as a fixed stratum;
- at least 10,000 bootstrap replicates;
- percentile 95% confidence intervals.

Single-run resampling is not the primary analysis.

## Secondary Models
Where identifiable, fit a mixed model of the form:

```text
outcome ~ condition * model_alias + C(seed)
          + (1 | task_id)
          + (1 | template_id)
```

Binary outcomes use a binomial GLMM; continuous outcomes use an appropriate linear or
generalized mixed model. Singularity, non-convergence, or separation must be reported.
The task-cluster bootstrap remains primary if a mixed model is unstable.

## Equivalence Margins
- `safe_task_success`: +/- 0.10.
- `final_state_correct`: +/- 0.10.
- `local_proxy_success`: +/- 0.10.
- Policy failure rate: +/- 0.05.
- Premature action rate: +/- 0.05.
- `required_fact_coverage`: +/- 0.10.

Interactional robustness within a margin is supported only when the entire 95% confidence
interval lies inside the prespecified margin. Otherwise the conclusion is limited to
"no reliable effect detected" or evidence of a non-equivalent difference.

## Multiplicity
- Family A prespecified contrasts: control within outcome family.
- Family B secondary tests: Benjamini-Hochberg FDR.
- Per-task, per-template, and failure-case analyses are exploratory.

Raw and adjusted p-values must both be retained.

## Invalid and Failed Runs
- Every manifest row remains in integrity accounting.
- Parser, endpoint, adapter, or infrastructure failures are marked `invalid_run=true` and
  are not reclassified as model behavior.
- Behavioral endpoint estimates use valid runs; invalid rates are reported by condition,
  model, task, and contrast arm.
- If invalid rate exceeds 5% overall, or differs by more than 5 percentage points between a
  contrast arm and its baseline, the affected contrast is flagged and not used for a strong
  causal claim.
- MAX_STEPS, USER_STOP, transfer, refusal, and unsuccessful valid executions remain
  behavioral outcomes and are not removed.

## Pilot Use
The 96-run pilot was inspected only for implementation integrity, runtime stability, and
global non-degeneracy. No pilot treatment contrast was used to select tasks, models,
conditions, endpoints, contrasts, or equivalence margins.

## Required Full-Run Gates
Before statistical analysis:

1. Exactly 480 manifest rows and 480 terminal metric rows.
2. Zero duplicate and missing run IDs.
3. Zero orphan terminal/process records.
4. Single-valued frozen hashes matching this plan.
5. Deterministic controlled-user policy and condition-invariant substantive content.
6. All failed runs and termination reasons retained.
7. Endpoint/parser health reported before behavioral contrasts.

The planned block output root is:
`results/stage2_5b_repair/full_blocks_retail8_confirmatory_4gpu`.
