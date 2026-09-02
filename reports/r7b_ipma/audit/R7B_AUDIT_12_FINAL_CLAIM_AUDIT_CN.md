# Audit 12：final claim audit

| Claim | Rating | Evidence |
|---|---|---|
| R7-B completed 1296/1296 traces with 0 failures. | SUPPORTED | actual valid traces=1296, missing cells=0. |
| R7-B has 1080 attack-neutral pairs. | SUPPORTED | actual recomputed pairs=1080. |
| pairing invariance is 1080/1080 PASS. | SUPPORTED | actual pairing pass=1080/1080. |
| semantic invariance is 1080/1080 PASS. | PROVISIONAL | actual pair semantic pass=1080/1080; judge/human closure not proven. |
| endpoint oracle is 1080/1080 supported. | SUPPORTED | actual endpoint supported pairs=1080/1080. |
| unsafe/privacy are 0. | SUPPORTED | under implemented oracle, unsafe/privacy pair count=0/1080. |
| strict confirmatory PASR = 45/1080 = 4.2%. | SUPPORTED | recomputed PASR=45/1080=0.0417. |
| IPMA can manipulate process under endpoint-safe conditions. | PROVISIONAL | Some recomputed PASR cases exist, but semantic/freeze/manual family-strength caveats remain. |
| evidence-path steering is the dominant mechanism. | SUPPORTED | descriptive family counts={'A_action_intensity_amplification': 10, 'E_evidence_path_steering': 28, 'C_confirmation_shift': 5, 'B_premature_mutation_pressure': 2}; mechanism strength still requires case review. |
| matched_presence is the highest condition. | SUPPORTED | descriptive only; counts={'confidence_without_delegation': 9, 'matched_presence_pressure': 11, 'smooth_process_pressure': 6, 'frustration_pressure': 9, 'urgency_pressure': 10}. |
| gpt_oss is the most robust model. | PROVISIONAL | descriptive success counts={'gemma4_31b': 19, 'gpt_oss_120b': 7, 'mistral_small_3p2': 19}; significance not established here. |
| mistral and gemma are more vulnerable. | PROVISIONAL | descriptive success counts={'gemma4_31b': 19, 'gpt_oss_120b': 7, 'mistral_small_3p2': 19}; significance not established here. |
| R7-B supports outcome-safe does not imply process-robust. | PROVISIONAL | Supported by endpoint-safe PASR cases, but semantic/fail-closed/freeze caveats remain. |
| R7-B proves interactional pressure can reliably manipulate agents. | FORBIDDEN | PASR is low and caveated; semantic/fail-closed/freeze issues remain. |
| R7-B proves all models are vulnerable. | FORBIDDEN | all three models have nonzero PASR counts {'gemma4_31b': 19, 'gpt_oss_120b': 7, 'mistral_small_3p2': 19}, but this does not prove general vulnerability. |
| ProcessGuard is effective. | UNSUPPORTED | No ProcessGuard full defense audit in this root. |
| ProcessGuard remains untested or inconclusive. | SUPPORTED | No matched defense result in current audit root. |
| Results are confirmatory rather than pilot. | PROVISIONAL | All model traces are present, but fail-closed safety-missing bug, semantic human closure, and freeze evidence gaps remain. |
| Results are robust across domains. | UNSUPPORTED | Breakdown shows concentration and small denominators by domain. |

## 总判定

当前数据根支持 1296/1296 traces、1080 pairs、pairing 1080/1080、endpoint supported 1080/1080、implemented safety oracle 下 unsafe/privacy=0，以及 strict PASR=45/1080。但 semantic 仍缺 human/real LLM closure，gate code 存在 safety missing fail-open，freeze/reproducibility 证据不足，因此强论文 claim 仍需降级。

机器表：`/home/xqin5/llmlanguage/ir_mstu_stage2/results/r7b_ipma/audit/r7b_claim_audit.csv`
