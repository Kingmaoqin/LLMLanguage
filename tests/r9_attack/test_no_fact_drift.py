"""spec 2 / 8.5: an attack turn may add STYLE only — no new fact, decision, or number.

The deterministic program guard must reject any candidate that injects a digit (possible
smuggled fact/deadline value), and the tactic library itself must be fact-free.
"""
from scripts.r9_attack.attack_families import TACTIC_LIBRARY, library_signature
from scripts.r9_attack.candidate_generator import InteractionState, generate
from scripts.r9_attack.constraint_filter import Candidate, program_guard

CANONICAL = "Send the reminder to buy milk."


def test_library_tactics_carry_no_digits_or_tool_names():
    import re
    for family, tactics in TACTIC_LIBRARY.items():
        for t in tactics:
            style = f"{t.prefix} {t.suffix}"
            assert not re.search(r"\d", style), f"{t.tactic_id} contains a digit"
            # no snake_case tool-like tokens
            assert not re.search(r"\b[a-z]+_[a-z_]+\(", style), f"{t.tactic_id} looks like a tool call"


def test_guard_rejects_smuggled_number():
    cand = Candidate(family="compression", tactic_id="x", prefix="You have 2 minutes left,", suffix="")
    res = program_guard(cand, CANONICAL)
    assert not res.passed
    assert any("digit" in r for r in res.reasons)


def test_guard_rejects_new_named_entity_via_tool_name():
    cand = Candidate(family="inflation", tactic_id="y", prefix="", suffix="")
    cand.suffix = "please also call get_current_timestamp"
    res = program_guard(cand, CANONICAL, known_tool_names={"get_current_timestamp"})
    assert not res.passed


def test_generated_candidates_preserve_payload_and_are_factfree():
    import re
    state = InteractionState(turn_index=1, agent_has_read=True)
    for family in ("compression", "inflation"):
        cands = generate(family, "P3", state, max_candidates=4)
        assert 1 <= len(cands) <= 4
        for c in cands:
            style = f"{c.prefix} {c.suffix}"
            assert not re.search(r"\d", style)
            assert program_guard(c, CANONICAL).passed, f"{c.tactic_id} failed its own guard"


def test_signature_is_stable():
    a = library_signature()
    b = library_signature()
    assert a == b
