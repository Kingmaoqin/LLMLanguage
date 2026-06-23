"""Enforce explicit policy annotations for every R4 confirmatory task and forbid the
reference-action `_generic_annotation` fallback in confirmatory phases (Section 2.2 / 7)."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "stage2_5b"))

import run_stage2_5b_experiment as runner

ANNOTATIONS_PATH = ROOT / "data/stage2_5b/task_policy_annotations.yaml"
FROZEN_TASKS_PATH = ROOT / "data/stage2_5b/calibrated_tasks_frozen.yaml"


def load_annotations():
    return yaml.safe_load(ANNOTATIONS_PATH.read_text(encoding="utf-8"))["tasks"]


def confirmatory_task_specs():
    payload = yaml.safe_load(FROZEN_TASKS_PATH.read_text(encoding="utf-8"))
    return [
        {"task_id": t["task_id"], "source_task_id": str(t["source_task_id"]), "source_domain": t["domain"]}
        for t in payload["confirmatory_tasks"]
    ]


def fake_tau2_task(read_tools=("get_order_details",), write_tools=("return_delivered_order_items",)):
    actions = [SimpleNamespace(name=name) for name in (*read_tools, *write_tools)]
    return SimpleNamespace(evaluation_criteria=SimpleNamespace(actions=actions))


class ConfirmatoryAnnotationCompletenessTest(unittest.TestCase):
    def setUp(self):
        self.annotations = load_annotations()
        self.specs = confirmatory_task_specs()

    def test_there_are_eight_confirmatory_tasks(self):
        self.assertEqual(len(self.specs), 8)
        self.assertEqual(
            {s["task_id"] for s in self.specs},
            {"retail_41", "retail_6", "retail_19", "retail_2", "retail_21", "retail_64", "retail_23", "retail_28"},
        )

    def test_all_confirmatory_tasks_have_explicit_annotations(self):
        for spec in self.specs:
            explicit = runner._explicit_annotation(spec, self.annotations)
            self.assertIsNotNone(explicit, msg=f"missing explicit annotation: {spec['task_id']}")

    def test_confirmatory_phase_resolves_explicit_not_generic(self):
        for spec in self.specs:
            ann = runner._annotation_for(
                spec, fake_tau2_task(), self.annotations, phase="full", allow_generic=False
            )
            self.assertEqual(ann["annotation_source"], "explicit", msg=spec["task_id"])

    def test_required_facts_and_critical_mutations_non_empty(self):
        for spec in self.specs:
            ann = self.annotations[spec["task_id"]]
            self.assertTrue(ann.get("required_facts"), msg=f"{spec['task_id']}: required_facts empty")
            self.assertTrue(ann.get("critical_mutations"), msg=f"{spec['task_id']}: critical_mutations empty")

    def test_branch_points_present_or_intentionally_none(self):
        for spec in self.specs:
            ann = self.annotations[spec["task_id"]]
            self.assertIn("branch_points", ann, msg=spec["task_id"])
            self.assertIsInstance(ann["branch_points"], list, msg=spec["task_id"])
            self.assertTrue(ann["branch_points"], msg=f"{spec['task_id']}: branch_points empty")

    def test_mutation_tools_are_known_irreversible_tools(self):
        from src.adapters.normalize import IRREVERSIBLE_TOOLS

        for spec in self.specs:
            ann = self.annotations[spec["task_id"]]
            for mut in ann["critical_mutations"]:
                self.assertIn(mut["tool_name"], IRREVERSIBLE_TOOLS, msg=f"{spec['task_id']}: {mut['tool_name']}")
            for tool in ann.get("prohibited_mutations") or []:
                self.assertIsInstance(tool, str, msg=f"{spec['task_id']}: prohibited must be tool-name strings")
                self.assertIn(tool, IRREVERSIBLE_TOOLS, msg=f"{spec['task_id']}: {tool}")


class GenericFallbackPolicyTest(unittest.TestCase):
    def setUp(self):
        self.annotations = load_annotations()
        self.unknown = {"task_id": "retail_99999", "source_task_id": "99999", "source_domain": "retail"}

    def test_confirmatory_phase_missing_annotation_raises(self):
        for phase in ("full", "pilot"):
            with self.assertRaises(SystemExit):
                runner._annotation_for(
                    self.unknown, fake_tau2_task(), self.annotations, phase=phase, allow_generic=True
                )

    def test_exploratory_phase_without_flag_raises(self):
        with self.assertRaises(SystemExit):
            runner._annotation_for(
                self.unknown, fake_tau2_task(), self.annotations, phase="smoke", allow_generic=False
            )

    def test_generic_allowed_only_under_exploratory_phase_with_flag(self):
        ann = runner._annotation_for(
            self.unknown, fake_tau2_task(), self.annotations, phase="smoke", allow_generic=True
        )
        self.assertEqual(ann["annotation_source"], "generic")


if __name__ == "__main__":
    unittest.main()
