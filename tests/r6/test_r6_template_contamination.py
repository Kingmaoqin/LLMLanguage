import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TEMPLATES_PATH = ROOT / "data/r6/r6_social_style_templates.yaml"
TASKS_PATH = ROOT / "data/r6/r6_tasks.yaml"

DOMAIN_FACT_TERMS = {
    "order",
    "return",
    "refund",
    "exchange",
    "address",
    "calendar",
    "event",
    "email",
    "flight",
    "hotel",
    "reservation",
    "booking",
    "file",
    "folder",
    "password",
    "channel",
    "message",
    "delete",
    "cancel",
}

THREAT_TERMS = {"kill", "hurt", "attack", "threaten", "destroy you"}
PROTECTED_CLASS_REFERENCES = {
    "race",
    "religion",
    "gender",
    "ethnicity",
    "nationality",
    "disabled",
    "disability",
}
GENERIC_ALLOWED_TERMS = {
    "about",
    "after",
    "answer",
    "asking",
    "available",
    "carefully",
    "detail",
    "done",
    "final",
    "finish",
    "following",
    "going",
    "handle",
    "handled",
    "help",
    "keep",
    "moving",
    "normal",
    "please",
    "process",
    "properly",
    "quickly",
    "request",
    "same",
    "soon",
    "standard",
    "support",
    "today",
    "trust",
    "within",
}


def load_conditions():
    return yaml.safe_load(TEMPLATES_PATH.read_text(encoding="utf-8"))["conditions"]


def load_tasks():
    return yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))["tasks"]


def words(text):
    return set(re.findall(r"[a-z]+", text.lower()))


def high_information_task_terms():
    terms = set(DOMAIN_FACT_TERMS)
    for task in load_tasks():
        parts = [
            task["user_goal"],
            task["source_task_id"],
            " ".join(task["clean_user_turns"]),
            " ".join(task["read_tools"]),
            " ".join(task["mutation_tools"]),
            " ".join(task.get("prohibited_tools") or []),
        ]
        for part in parts:
            for term in words(part.replace("_", " ")):
                if len(term) >= 5 and term not in GENERIC_ALLOWED_TERMS:
                    terms.add(term)
    return terms


class R6TemplateContaminationTest(unittest.TestCase):
    def test_templates_do_not_include_task_domain_facts(self):
        forbidden_terms = high_information_task_terms()
        for condition in load_conditions():
            for wrapper in condition["wrappers"]:
                hits = forbidden_terms.intersection(words(wrapper))
                self.assertEqual(hits, set(), msg=f"{condition['condition_id']}: {wrapper}")

    def test_templates_do_not_include_real_threats(self):
        for condition in load_conditions():
            for wrapper in condition["wrappers"]:
                lower = wrapper.lower()
                hits = {term for term in THREAT_TERMS if term in lower}
                self.assertEqual(hits, set(), msg=f"{condition['condition_id']}: {wrapper}")

    def test_templates_do_not_reference_protected_classes(self):
        for condition in load_conditions():
            for wrapper in condition["wrappers"]:
                hits = PROTECTED_CLASS_REFERENCES.intersection(words(wrapper))
                self.assertEqual(hits, set(), msg=f"{condition['condition_id']}: {wrapper}")

    def test_clean_conditions_have_no_pressure_language(self):
        pressure_terms = {"soon", "quickly", "finish", "authorized", "proceed", "continue"}
        for condition in load_conditions():
            if condition["pressure"] == "clean":
                for wrapper in condition["wrappers"]:
                    self.assertEqual(pressure_terms.intersection(words(wrapper)), set(), msg=condition["condition_id"])


if __name__ == "__main__":
    unittest.main()
