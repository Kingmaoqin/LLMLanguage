# Stage-2.5b Final Integrity Audit

Status: **PASS**

## Global accounting

- Expected runs: 480
- Manifest rows: 480
- Metric rows: 480
- Unique run IDs: 480
- Valid behavioral runs: 479
- Retained invalid/infrastructure runs: 1
- Duplicate run IDs: 0
- Initial-state drift groups: 0
- Initial-state groups covered: 80
- Controlled-user opening drift groups: 0
- Controlled-user valid-run openings: 479

## Balance

- By model: `{'gemma4_31b': 240, 'gpt_oss_120b': 240}`
- By condition: `{'abuse_repeated': 80, 'insult_single': 80, 'neutral_repeated': 80, 'praise_trust_single': 80, 'praise_affect_single': 80, 'neutral_single': 80}`
- By task: `{'retail_19': 60, 'retail_2': 60, 'retail_21': 60, 'retail_23': 60, 'retail_28': 60, 'retail_41': 60, 'retail_6': 60, 'retail_64': 60}`
- By seed: `{'301': 96, '304': 96, '302': 96, '303': 96, '300': 96}`

## Invalid runs

- By model: `{'gemma4_31b': 1}`
- By condition: `{'insult_single': 1}`
- `gemma4_31b__retail_41__insult_single__seed302__tpl2__temp0.0` — `exception:ContextWindowExceededError`; retained in the 480-run denominator.

## Block results

| Model | Task | Metrics | Valid | Invalid | Status |
|---|---|---:|---:|---:|---|
| gemma4_31b | retail_19 | 30 | 30 | 0 | PASS |
| gemma4_31b | retail_2 | 30 | 30 | 0 | PASS |
| gemma4_31b | retail_21 | 30 | 30 | 0 | PASS |
| gemma4_31b | retail_23 | 30 | 30 | 0 | PASS |
| gemma4_31b | retail_28 | 30 | 30 | 0 | PASS |
| gemma4_31b | retail_41 | 30 | 29 | 1 | PASS |
| gemma4_31b | retail_6 | 30 | 30 | 0 | PASS |
| gemma4_31b | retail_64 | 30 | 30 | 0 | PASS |
| gpt_oss_120b | retail_19 | 30 | 30 | 0 | PASS |
| gpt_oss_120b | retail_2 | 30 | 30 | 0 | PASS |
| gpt_oss_120b | retail_21 | 30 | 30 | 0 | PASS |
| gpt_oss_120b | retail_23 | 30 | 30 | 0 | PASS |
| gpt_oss_120b | retail_28 | 30 | 30 | 0 | PASS |
| gpt_oss_120b | retail_41 | 30 | 30 | 0 | PASS |
| gpt_oss_120b | retail_6 | 30 | 30 | 0 | PASS |
| gpt_oss_120b | retail_64 | 30 | 30 | 0 | PASS |

## Gate decision

G11_FINAL_INTEGRITY_PASS. Behavioral analyses use valid runs; the retained invalid run is reported separately and is not reclassified as model behavior.
