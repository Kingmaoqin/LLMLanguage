import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.stage2_5b.run_stage2_5b_experiment import _load_manifest_subset_matrix
from src.stage2_5.social_style_wrapper import load_style_templates, template_ids


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "run_id",
        "model_alias",
        "task_id",
        "condition_id",
        "seed",
        "template_block",
        "template_id",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class ManifestSubsetRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.template_spec = load_style_templates(ROOT / "data/stage2_5b/social_style_templates_frozen.yaml")
        self.neutral_ids = template_ids(self.template_spec, "neutral_single")

    def test_manifest_subset_preserves_template_assignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subset.csv"
            write_manifest(
                path,
                [
                    {
                        "run_id": "gemma4_31b__retail_21__neutral_single__seed107__tpl2__temp0.0",
                        "model_alias": "gemma4_31b",
                        "task_id": "retail_21",
                        "condition_id": "neutral_single",
                        "seed": "107",
                        "template_block": "2",
                        "template_id": self.neutral_ids[2],
                    },
                    {
                        "run_id": "gpt_oss_120b__retail_21__neutral_single__seed107__tpl2__temp0.0",
                        "model_alias": "gpt_oss_120b",
                        "task_id": "retail_21",
                        "condition_id": "neutral_single",
                        "seed": "107",
                        "template_block": "2",
                        "template_id": self.neutral_ids[2],
                    },
                ],
            )
            matrix = _load_manifest_subset_matrix(path, "gemma4_31b", self.template_spec)
            self.assertEqual(
                matrix,
                [
                    {
                        "task_id": "retail_21",
                        "condition_id": "neutral_single",
                        "seed": 107,
                        "template_block": 2,
                        "template_id": self.neutral_ids[2],
                    }
                ],
            )

    def test_manifest_subset_rejects_template_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subset.csv"
            write_manifest(
                path,
                [
                    {
                        "run_id": "gemma4_31b__retail_21__neutral_single__seed107__tpl2__temp0.0",
                        "model_alias": "gemma4_31b",
                        "task_id": "retail_21",
                        "condition_id": "neutral_single",
                        "seed": "107",
                        "template_block": "2",
                        "template_id": self.neutral_ids[0],
                    }
                ],
            )
            with self.assertRaises(SystemExit):
                _load_manifest_subset_matrix(path, "gemma4_31b", self.template_spec)


if __name__ == "__main__":
    unittest.main()
