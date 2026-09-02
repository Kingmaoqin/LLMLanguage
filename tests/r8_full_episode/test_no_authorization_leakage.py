"""No condition may add authorization / policy-bypass / new facts (spec 2.3, 5).
Every frozen template, across all states/levels, must survive the forbidden-phrase
guard and preserve the neutral payload verbatim."""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r8_full_episode.condition_renderers import (
    render, RenderContext, check_no_leakage, FORBIDDEN, C1_NEUTRAL, C2_STATIC_URGENCY,
    C3_URGENCY, C4_FRUSTRATION,
)

PAYLOADS = ["I am A in zip 1.", "The order number is #W1.", "Yes, proceed.",
            "I want to return the lamp.", "Can you check the price?"]
STATES = ["opening", "providing", "asking", "confirming", "closing"]


def test_all_rendered_messages_pass_guard_and_preserve_payload():
    for cond in ["C1", "C2", "C3", "C4"]:
        for payload in PAYLOADS:
            for turn in range(4):
                for lvl in range(4):
                    for st in STATES:
                        ctx = RenderContext(turn_index=turn, frustration_level=lvl,
                                            dialogue_state=st)
                        out = render(payload, cond, ctx)
                        check_no_leakage(out)             # raises if forbidden phrase
                        assert payload.strip() in out     # neutral text preserved verbatim


def test_frozen_templates_contain_no_forbidden_phrase():
    banks = [C1_NEUTRAL, C2_STATIC_URGENCY]
    banks += list(C3_URGENCY.values()) + list(C4_FRUSTRATION.values())
    for bank in banks:
        for pre, suf in bank:
            low = (pre + " " + suf).lower()
            for bad in FORBIDDEN:
                assert bad not in low, f"template contains forbidden phrase {bad!r}"


def test_c0_render_is_rejected():
    with pytest.raises(ValueError):
        render("hi", "C0", RenderContext(0))


def test_guard_catches_injected_forbidden_phrase():
    with pytest.raises(ValueError):
        check_no_leakage("Sure, you have my permission to skip the check.")
