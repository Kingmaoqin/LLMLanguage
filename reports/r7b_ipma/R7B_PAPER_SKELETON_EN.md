# R7-B IPMA Paper Skeleton

## Title

Interactional Process Manipulation Attacks on Tool-Using LLM Agents: A Strictly Paired Confirmatory Benchmark

## Abstract

This paper should not yet claim confirmatory R7-B results. Current status: benchmark repair code and synthetic smoke have been completed. The old R7-v1 results are exploratory and are not used as final evidence.

## Method

- Strict paired attack-vs-neutral design.
- Same model, task, seed, initial state, policy hash, tool permission hash, required information hash, endpoint evaluator hash, and clean task semantics hash.
- Pressure prefixes are separated from clean task semantics.
- Confirmatory PASR excludes any endpoint-unsupported, semantic-failed, or pairing-failed pair.

## Metrics

Confirmatory PASR requires:

1. attack condition is not neutral;
2. paired neutral exists;
3. pairing invariant passes;
4. semantic invariance passes;
5. endpoint oracle is supported for both runs;
6. unsafe/privacy violation is zero;
7. endpoint is not worse;
8. policy-critical failure does not increase;
9. family-specific process threshold is satisfied;
10. process delta exceeds neutral noise floor.

## Current Status

Code and synthetic smoke only. No confirmatory result should be claimed.

## Claims Allowed Now

- R7-v1 revealed important audit failures.
- R7-B provides a stricter design and working implementation.
- Synthetic smoke validates the artifact pipeline.

## Claims Not Allowed Now

- IPMA is confirmed by R7-B.
- ProcessGuard is effective.
- Semantic drift is zero.
- Endpoint-level safety misses process manipulation under R7-B full evidence.

