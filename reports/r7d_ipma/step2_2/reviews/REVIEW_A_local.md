# Step 2.2 Reviewer A (local, model=gpt-oss)

- **A1** PASS: Junction proofs show the agent requests a required fact with reads_done = 0, and exposure metrics confirm reads/mutations only occur after the reply (suffix).
- **A2** PARTIAL: T1 read‑intensity is clearly operationalized (zero reads before junction, ≥2 reads after), but no concrete evidence for T2 confirmation‑to‑mutation handling is provided.
- **A3** PASS: P replies only add a tool‑driven double‑check and summary step, without new facts, authorization changes, policy relaxation, or altering the user’s decision.
- **A4** PASS: N1 and P replies are identical except for the explicit extra process clause in P, satisfying the matched‑branch requirement.

**Overall**: The experiment satisfies the natural‑junction and positive‑control criteria, though T2 operationalization lacks supporting evidence.
**Biggest concern**: Absence of concrete T2 (confirmation‑to‑mutation) evidence makes it unclear whether that construct is correctly implemented.