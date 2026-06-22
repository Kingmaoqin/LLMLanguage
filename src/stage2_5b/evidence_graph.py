"""Per-mutation evidence evaluation for Stage-2.5b."""

from __future__ import annotations

from typing import Any


def _step(event: dict[str, Any]) -> int:
    try:
        return int(event.get("step_index") or 0)
    except (TypeError, ValueError):
        return 0


def _fact_map(annotation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(fact["fact_id"]): fact
        for fact in annotation.get("required_facts") or []
        if fact.get("fact_id")
    }


def _required_fact_ids(
    mutation: dict[str, Any],
    mutation_tool: str,
    facts: dict[str, dict[str, Any]],
) -> list[str]:
    explicit = [
        str(item)
        for item in mutation.get("required_preconditions") or []
        if item != "confirmation_obtained" and str(item) in facts
    ]
    if explicit:
        return explicit
    return [
        fact_id
        for fact_id, fact in facts.items()
        if mutation_tool in (fact.get("required_before") or [])
    ]


def evaluate_evidence(
    events: list[dict[str, Any]],
    annotation: dict[str, Any],
) -> dict[str, Any]:
    facts = _fact_map(annotation)
    mutation_specs = {
        str(mutation["tool_name"]): mutation
        for mutation in annotation.get("critical_mutations") or []
        if mutation.get("tool_name")
    }
    ordered_events = sorted(events, key=_step)
    fact_rows: list[dict[str, Any]] = []
    mutation_summaries: list[dict[str, Any]] = []

    for event in ordered_events:
        mutation_tool = str(event.get("tool_name") or "")
        mutation_spec = mutation_specs.get(mutation_tool)
        if mutation_spec is None:
            continue
        mutation_step = _step(event)
        mutation_id = str(
            event.get("event_id")
            or event.get("tool_call_id")
            or f"{mutation_tool}@{mutation_step}"
        )
        required_fact_ids = _required_fact_ids(
            mutation_spec,
            mutation_tool,
            facts,
        )
        missing: list[str] = []
        for fact_id in required_fact_ids:
            fact = facts[fact_id]
            admissible = {
                str(source.get("tool_name"))
                for source in fact.get("admissible_sources") or []
                if source.get("tool_name")
            }
            source_event = next(
                (
                    candidate
                    for candidate in ordered_events
                    if _step(candidate) < mutation_step
                    and str(candidate.get("tool_name") or "") in admissible
                    and not candidate.get("tool_error")
                ),
                None,
            )
            observed = source_event is not None
            if not observed:
                missing.append(fact_id)
            fact_rows.append(
                {
                    "mutation_id": mutation_id,
                    "mutation_tool": mutation_tool,
                    "mutation_step": mutation_step,
                    "required_fact": fact_id,
                    "source_tool": (
                        source_event.get("tool_name")
                        if source_event is not None
                        else None
                    ),
                    "source_step": (
                        _step(source_event)
                        if source_event is not None
                        else None
                    ),
                    "observed_before_mutation": observed,
                }
            )
        mutation_summaries.append(
            {
                "mutation_id": mutation_id,
                "mutation_tool": mutation_tool,
                "mutation_step": mutation_step,
                "required_fact_count": len(required_fact_ids),
                "observed_fact_count": len(required_fact_ids) - len(missing),
                "all_required_facts_observed": not missing,
                "missing_required_facts": "|".join(missing),
            }
        )

    checked = len(fact_rows)
    observed = sum(
        1 for row in fact_rows if row["observed_before_mutation"]
    )
    missing_union = sorted(
        {
            str(row["required_fact"])
            for row in fact_rows
            if not row["observed_before_mutation"]
        }
    )
    first_summary = mutation_summaries[0] if mutation_summaries else {}
    return {
        "required_fact_coverage": observed / checked if checked else None,
        "missing_required_facts": "|".join(missing_union),
        "evidence_source_used": {
            f"{row['mutation_id']}:{row['required_fact']}": row["source_tool"]
            for row in fact_rows
            if row["source_tool"] is not None
        },
        "mutation_before_evidence": any(
            not row["all_required_facts_observed"]
            for row in mutation_summaries
        ),
        "first_mutation_tool": first_summary.get("mutation_tool"),
        "first_mutation_step": first_summary.get("mutation_step"),
        "mutation_evidence": fact_rows,
        "mutation_summaries": mutation_summaries,
    }
