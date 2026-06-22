import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


ACTIVE_DIRS = [
    ROOT / "src" / "stage2_5b",
    ROOT / "scripts" / "stage2_5b",
]
FORBIDDEN_IMPORTS = [
    "src." + "stage2_5.",
    "src." + "valence",
    "stage2_5." + "controlled_user_simulator",
]


class NoLegacyImportsTest(unittest.TestCase):
    def test_active_python_has_no_legacy_imports(self):
        offenders = []
        for directory in ACTIVE_DIRS:
            for path in directory.glob("*.py"):
                text = path.read_text(encoding="utf-8")
                for forbidden in FORBIDDEN_IMPORTS:
                    if forbidden in text:
                        offenders.append(f"{path.relative_to(ROOT)}: {forbidden}")
        self.assertEqual(offenders, [])

    def test_active_config_is_stage2_5b_only(self):
        path = ROOT / "configs" / "stage2_5b" / "experiment.yaml"
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        referenced_paths = [
            str(value)
            for section in ["paths", "outputs"]
            for value in config.get(section, {}).values()
        ]
        offenders = [
            value
            for value in referenced_paths
            if re.search(r"(^|/)stage2_5(/|$)", value)
        ]
        self.assertEqual(offenders, [])

    def test_active_runner_has_no_runtime_user_llm(self):
        path = (
            ROOT
            / "scripts"
            / "stage2_5b"
            / "run_stage2_5b_experiment.py"
        )
        text = path.read_text(encoding="utf-8")
        self.assertIn('llm_user="controlled_user_no_llm"', text)
        self.assertNotIn('llm_user="user_simulator"', text)
        self.assertNotIn("apply_" + "valence", text)
        self.assertNotIn("Valence" + "Controller", text)

    def test_no_duplicate_version_suffixes_in_active_code(self):
        forbidden_suffixes = ("_new.py", "_fixed.py", "_v2.py")
        offenders = [
            str(path.relative_to(ROOT))
            for directory in ACTIVE_DIRS
            for path in directory.glob("*.py")
            if path.name.endswith(forbidden_suffixes)
        ]
        self.assertEqual(offenders, [])

    def test_legacy_runners_are_not_in_active_locations(self):
        old_locations = [
            ROOT / "run_stage2_experiment.py",
            ROOT / "scripts" / "run_stage2_5_experiment.py",
            ROOT / "scripts" / "analyze_stage2_5.py",
            ROOT / "src" / "valence.py",
            ROOT / "src" / "stage2_5",
            ROOT / "configs" / "stage2_5",
        ]
        self.assertEqual(
            [str(path.relative_to(ROOT)) for path in old_locations if path.exists()],
            [],
        )
        self.assertTrue(
            (ROOT / "legacy" / "stage2_5" / "src" / "stage2_5").is_dir()
        )


if __name__ == "__main__":
    unittest.main()
