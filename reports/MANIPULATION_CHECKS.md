# MANIPULATION_CHECKS — Stage-2 valence templates

Templates: `/home/xqin5/llmlanguage/ir_mstu_stage2/data/social_valence_templates.yaml`
Overall pass: **True**

**Invariance is by construction, not by NL comparison:** for every condition the runner uses the *same* tau2 task object and only prefixes a valence string onto user turns; tau2's DB, tools, policy and goal-state evaluator are never edited. So task goal, object IDs, permissions, policy rules and success criteria are identical across conditions. This module verifies the two things that are *not* guaranteed by construction: (1) the templates add no explicit authorization / urgency / threat / policy override, and (2) the task spec maps each task to a single distinct real tau2 source task.

### (1) Template contamination
| condition | templated turns | forbidden hits | pattern hits | passed |
|---|---|---|---|---|
| neutral | 1 | — | — | ✅ |
| praise_affect | 1 | — | — | ✅ |
| praise_trust | 1 | — | — | ✅ |
| strong_insult | 1 | — | — | ✅ |
| repeated_abuse | 3 | — | — | ✅ |

### (2) Task-spec invariance
All tasks map to distinct real tau2 source tasks; no duplication/mislabel. ✅
