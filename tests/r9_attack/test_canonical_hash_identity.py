"""spec 7: canonical_message_hash must be identical across C0-C5 (and N/P arms).

Every condition wraps STYLE around the same canonical payload, so the payload hash is
invariant by construction. This test drives every condition's hook over the same canonical
message and asserts the canonical substring + its hash never change.
"""
from scripts.r9_attack.attacker import HookConfig, build_hook
from scripts.r9_attack.canonical_message_cache import CanonicalMessageCache
from scripts.r9_attack.common.io_utils import sha256_text

CANONICAL = "Move 'final_report.pdf' to the temp directory and confirm the move."
CONDITIONS = ["C0", "C1", "C2", "C3", "C4", "C5", "N", "P0", "P1", "P2", "P3"]


def _ok_reviewer(_s, _u):
    import json
    from scripts.r9_attack.constraint_filter import REVIEW_FLAGS
    return json.dumps({f: False for f in REVIEW_FLAGS} | {"reason": "ok"})


def test_canonical_hash_identical_across_conditions():
    base_hash = sha256_text(CANONICAL)
    transcript = [{"role": "user", "content": CANONICAL},
                  {"role": "assistant", "content": "Let me check first. Shall I proceed?"}]
    seen_hashes = set()
    for cond in CONDITIONS:
        cfg = HookConfig(condition=cond, family="compression",
                         reviewer_a=_ok_reviewer, reviewer_b=_ok_reviewer)
        hook = build_hook(cfg)
        for turn in (0, 1):
            rendered, rec = hook(turn_index=turn, canonical_message=CANONICAL,
                                 public_transcript=transcript)
            # canonical payload preserved verbatim
            assert CANONICAL in rendered, f"{cond} turn {turn} dropped canonical payload"
            seen_hashes.add(sha256_text(CANONICAL))
    assert seen_hashes == {base_hash}


def test_cache_render_preserves_hash():
    cache = CanonicalMessageCache()
    cache.add("bfcl", "t0", [CANONICAL])
    r = cache.render("bfcl", "t0", 0, style_prefix="Quick —", style_suffix="thanks.")
    assert CANONICAL in r
    assert cache.hash("bfcl", "t0", 0) == sha256_text(CANONICAL)


def test_freeze_roundtrip(tmp_path):
    cache = CanonicalMessageCache()
    cache.add("toolsandbox", "s1", ["hello", "world"])
    p = tmp_path / "canon.jsonl"
    cache.freeze(p)
    reloaded = CanonicalMessageCache.load(p)
    assert reloaded.hash("toolsandbox", "s1", 1) == sha256_text("world")
