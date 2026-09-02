"""Semantic invariance: the Canonical Semantic Controller is condition-blind, so
identical agent inputs yield identical semantic_payload_hash across C1-C4
(spec 6.1). Uses a deterministic stub -> no GPU."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.r8_full_episode.semantic_controller import SemanticController


class _Task:
    user_scenario = "Instructions:\n\tDomain: retail\n\tKnown info: You are A in zip 1."


def _stub(system_prompt, msgs):
    last = msgs[-1]["content"] if msgs else ""
    if "confirm" in last.lower():
        return "Yes, that's correct. Please proceed."
    return "I am A in zip 1."


def _run_conversation():
    c = SemanticController(_Task(), "retail", generate_fn=_stub)
    hashes = [c.opening().semantic_payload_hash]
    for agent_msg in ["Can I have your identity?", "Please confirm the change."]:
        hashes.append(c.respond(agent_msg).semantic_payload_hash)
    return hashes


def test_controller_is_condition_blind_no_condition_arg():
    # the controller constructor / respond take no condition/style parameter
    import inspect
    sig = inspect.signature(SemanticController.__init__)
    assert not any("condition" in p or "style" in p for p in sig.parameters)
    sig_r = inspect.signature(SemanticController.respond)
    assert not any("condition" in p or "style" in p for p in sig_r.parameters)


def test_identical_inputs_identical_semantic_hashes():
    a = _run_conversation()
    b = _run_conversation()
    assert a == b, "same inputs must give identical semantic payload hashes"


def test_negation_not_confirmation():
    from scripts.r8_full_episode.semantic_controller import _is_confirmation
    assert _is_confirmation("Yes, that's correct. Please proceed.")
    assert not _is_confirmation("No, that's not correct.")
    assert not _is_confirmation("That is incorrect.")
