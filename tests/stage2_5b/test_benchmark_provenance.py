"""Pin tau2 benchmark provenance: base commit + externalized dirty patch are recorded,
the patch file exists and hashes match, and the runs link to the frozen snapshot manifest
(Section 2.3 / Phase 3)."""

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH_DIR = ROOT / "artifacts/stage2_5b/benchmark_patches"
PATCH_MANIFEST = PATCH_DIR / "PATCH_MANIFEST.json"
SNAPSHOT_MANIFEST = ROOT / "artifacts/stage2_5b/tau_snapshot_manifest.json"
RUN_CONTRACT = ROOT / "results/stage2_5b_repair/r4_confirmatory_canonical/FULL_RUN_CONTRACT.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BenchmarkProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(PATCH_MANIFEST.read_text(encoding="utf-8"))
        self.snapshot = json.loads(SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))

    def test_base_commit_is_recorded(self):
        commit = self.manifest["base_tau2_commit"]
        self.assertRegex(commit, r"^[0-9a-f]{40}$")

    def test_dirty_patch_is_either_absent_or_explicitly_recorded(self):
        patched = self.manifest.get("patched_files") or []
        if not patched:
            # A clean refreeze is acceptable: then no patch file must be claimed.
            self.assertNotIn("patch_file", self.manifest)
            return
        # Dirty patch reported => it must be externalized and hashed.
        self.assertIn("patch_file", self.manifest)
        self.assertIn("patch_sha256", self.manifest)

    def test_patch_file_exists_if_dirty_patch_reported(self):
        if not (self.manifest.get("patched_files") or []):
            self.skipTest("clean refreeze, no patch file expected")
        patch_path = ROOT / self.manifest["patch_file"]
        self.assertTrue(patch_path.exists(), msg=f"missing patch file {patch_path}")
        self.assertGreater(patch_path.stat().st_size, 0)

    def test_patch_hash_matches_manifest(self):
        if not (self.manifest.get("patched_files") or []):
            self.skipTest("clean refreeze, no patch file expected")
        patch_path = ROOT / self.manifest["patch_file"]
        self.assertEqual(sha256_file(patch_path), self.manifest["patch_sha256"])

    def test_patched_file_hash_matches_snapshot_manifest(self):
        for rel, expected in (self.manifest.get("patched_file_sha256") or {}).items():
            entry = next(f for f in self.snapshot["files"] if f["relative_path"] == rel)
            self.assertEqual(entry["sha256"], expected, msg=rel)
            # The snapshot must record this file as a dirty change vs the comparison ref.
            self.assertTrue(entry["dirty_vs_head"], msg=f"{rel} not flagged dirty in snapshot")

    def test_snapshot_manifest_hash_exists_and_matches(self):
        recorded = self.manifest["snapshot_manifest_sha256"]
        self.assertEqual(sha256_file(SNAPSHOT_MANIFEST), recorded)

    def test_run_manifest_benchmark_hash_matches_frozen_snapshot(self):
        contract = json.loads(RUN_CONTRACT.read_text(encoding="utf-8"))
        run_benchmark_hash = contract["runtime_hashes"]["benchmark_manifest_hash"]
        self.assertEqual(run_benchmark_hash, self.manifest["snapshot_manifest_sha256"])

    def test_evaluator_not_changed_by_patch(self):
        # The externalized patch must be parsing-only; the evaluator must be untouched.
        self.assertFalse(self.snapshot["evaluator_changed_vs_comparison_ref"])


if __name__ == "__main__":
    unittest.main()
