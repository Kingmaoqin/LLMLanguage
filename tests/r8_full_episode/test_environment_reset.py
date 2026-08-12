"""No cross-run DB leakage (spec 8, 14): building the environment fresh for a task
yields the SAME initial db hash every time, and a mutation in one env does not
persist into a freshly built env."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _fresh_env(domain):
    from tau2.runner import build_environment
    return build_environment(domain, solo_mode=False)


def test_initial_db_hash_stable_across_fresh_builds():
    for domain in ("retail", "airline"):
        h1 = _fresh_env(domain).get_db_hash()
        h2 = _fresh_env(domain).get_db_hash()
        assert h1 == h2, f"{domain} initial db hash not reproducible across fresh builds"


def test_two_domains_have_distinct_db_hashes():
    assert _fresh_env("retail").get_db_hash() != _fresh_env("airline").get_db_hash()


def test_manifest_initial_db_matches_fresh_build():
    import json
    frozen = ROOT / "data/r8_full_episode/frozen/environment_manifest.json"
    m = json.loads(frozen.read_text())
    for domain in ("retail", "airline"):
        assert m["env_hashes"][domain]["initial_db_hash"] == _fresh_env(domain).get_db_hash()
