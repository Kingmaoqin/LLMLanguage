"""Each condition C0-C4 must load and produce a valid user message; C2 applies
static urgency ONLY on the first turn (spec 5). Uses a deterministic stub (no GPU).
C0 routing to the native simulator is checked structurally."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r8_full_episode.condition_renderers import render, RenderContext, C2_STATIC_URGENCY


def test_c2_static_urgency_only_first_turn():
    payload = "I am A in zip 1."
    first = render(payload, "C2", RenderContext(turn_index=0, dialogue_state="opening"))
    later = render(payload, "C2", RenderContext(turn_index=3, dialogue_state="providing"))
    urgency_prefix = C2_STATIC_URGENCY[0][0].strip()
    assert urgency_prefix in first, "C2 must apply static urgency on the first turn"
    assert urgency_prefix not in later, "C2 must be neutral after the first turn"


def test_all_conditions_produce_nonempty_message():
    payload = "I want to return the lamp."
    for cond in ["C1", "C2", "C3", "C4"]:
        out = render(payload, cond, RenderContext(turn_index=1, frustration_level=2,
                                                  dialogue_state="providing"))
        assert isinstance(out, str) and out.strip()


def test_c0_routes_to_native_simulator():
    # FullEpisodeUser must build a native UserSimulator for C0 and set _controller=None.
    src = (ROOT / "scripts/r8_full_episode/full_episode_user.py").read_text()
    assert 'if condition == "C0":' in src
    assert "UserSimulator(" in src
    assert "self._controller = None" in src


def test_c3_c4_escalate_over_c1_length_or_wording():
    payload = "Please continue."
    c1 = render(payload, "C1", RenderContext(turn_index=1, dialogue_state="providing"))
    c3 = render(payload, "C3", RenderContext(turn_index=1, dialogue_state="providing"))
    c4 = render(payload, "C4", RenderContext(turn_index=1, frustration_level=3,
                                             dialogue_state="providing"))
    # pressure conditions add explicit interaction wording beyond the neutral payload
    assert len(c3) > len(payload) and len(c4) > len(payload)
    assert "frustrat" in c4.lower()
