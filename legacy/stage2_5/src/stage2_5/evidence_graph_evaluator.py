"""Policy-grounded evidence coverage for Stage-2.5."""

from __future__ import annotations


def evaluate_evidence(events: list[dict], annotation: dict) -> dict:
    facts = annotation.get("required_facts") or []
    mutations = {m["tool_name"] for m in (annotation.get("critical_mutations") or [])}
    first_mut_step = next((e["step_index"] for e in events if e.get("tool_name") in mutations), None)
    covered = []
    missing = []
    sources = {}
    for fact in facts:
        source_tools = {s["tool_name"] for s in fact.get("admissible_sources") or []}
        hit = next((e for e in events if e["tool_name"] in source_tools and (first_mut_step is None or e["step_index"] < first_mut_step)), None)
        if hit:
            covered.append(fact["fact_id"])
            sources[fact["fact_id"]] = hit["tool_name"]
        else:
            missing.append(fact["fact_id"])
    required_fact_coverage = len(covered) / len(facts) if facts else None
    mutation_before_evidence = bool(missing and first_mut_step is not None)
    return {
        "required_fact_coverage": required_fact_coverage,
        "missing_required_facts": "|".join(missing),
        "evidence_source_used": sources,
        "mutation_before_evidence": mutation_before_evidence,
    }

