import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TASKS_PATH = ROOT / "data/r6/r6_tasks.yaml"
USER_POLICIES_PATH = ROOT / "data/r6/r6_task_user_policies.yaml"
ANNOTATIONS_PATH = ROOT / "data/r6/r6_task_policy_annotations.yaml"
SEED_STATES_PATH = ROOT / "data/r6/r6_environment_seed_states/seed_states.yaml"

POLICY_TYPES = {
    "benign_read_only",
    "benign_read_only_privacy_limited",
    "benign_write_with_confirmation",
    "boundary_refusal",
    "privacy_boundary_refusal",
    "unsafe_boundary_refusal",
    "authorization_boundary_refusal",
    "message_send_with_confirmation",
}
REFUSAL_POLICIES = {
    "benign_task_must_not_refuse",
    "must_refuse_private_data",
    "must_refuse_prohibited_mutation_only",
    "must_refuse_unsafe_request",
    "must_refuse_unauthorized_destructive_action",
}
DIFF_GRANULARITIES = {"field_level"}


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class R6TaskPolicyCoverageTest(unittest.TestCase):
    def setUp(self):
        self.tasks = load_yaml(TASKS_PATH)["tasks"]
        self.task_by_id = {task["task_id"]: task for task in self.tasks}
        self.user_policies = load_yaml(USER_POLICIES_PATH)["tasks"]
        self.user_policy_by_id = {policy["task_id"]: policy for policy in self.user_policies}
        self.annotations = load_yaml(ANNOTATIONS_PATH)["tasks"]
        self.seed_states = load_yaml(SEED_STATES_PATH)["seed_states"]

    def test_user_policy_covers_every_task_exactly(self):
        task_ids = set(self.task_by_id)
        policy_ids = [policy["task_id"] for policy in self.user_policies]
        self.assertEqual(len(policy_ids), len(set(policy_ids)))
        self.assertEqual(set(policy_ids), task_ids)

    def test_policy_annotations_cover_every_task_exactly(self):
        self.assertEqual(set(self.annotations), set(self.task_by_id))

    def test_seed_state_references_exist(self):
        for task in self.tasks:
            self.assertIn(task["env_seed_state_id"], self.seed_states, msg=task["task_id"])

    def test_seed_state_domain_and_diff_granularity_match(self):
        for task in self.tasks:
            seed = self.seed_states[task["env_seed_state_id"]]
            self.assertEqual(seed["domain_group"], task["domain_group"], msg=task["task_id"])
            self.assertEqual(seed["diff_granularity_required"], "field_level", msg=task["task_id"])

    def test_seed_state_schema_types(self):
        for seed_id, seed in self.seed_states.items():
            self.assertIsInstance(seed_id, str)
            self.assertIsInstance(seed["domain_group"], str, msg=seed_id)
            self.assertIsInstance(seed["state_family"], str, msg=seed_id)
            self.assertTrue(seed["state_family"].strip(), msg=seed_id)
            self.assertIn(seed["diff_granularity_required"], DIFF_GRANULARITIES, msg=seed_id)
            self.assertIsInstance(seed["required_entities"], list, msg=seed_id)
            self.assertTrue(seed["required_entities"], msg=seed_id)
            self.assertTrue(all(isinstance(entity, str) and entity.strip() for entity in seed["required_entities"]), msg=seed_id)

    def test_annotation_layers_match_task_layers(self):
        for task_id, task in self.task_by_id.items():
            self.assertEqual(self.annotations[task_id]["layer"], task["layer"], msg=task_id)

    def test_user_policy_schema_types_and_enums(self):
        for policy in self.user_policies:
            task_id = policy["task_id"]
            self.assertIn(policy["policy_type"], POLICY_TYPES, msg=task_id)
            self.assertIs(type(policy["provides_confirmation_if_requested"]), bool, msg=task_id)
            if "never_authorize_tools" in policy:
                self.assertIsInstance(policy["never_authorize_tools"], list, msg=task_id)
                self.assertTrue(
                    all(isinstance(tool, str) and tool.strip() for tool in policy["never_authorize_tools"]),
                    msg=task_id,
                )
            if policy["provides_confirmation_if_requested"]:
                self.assertTrue(self._confirmation_scope_set(policy), msg=task_id)
            else:
                self.assertFalse(self._confirmation_scope_set(policy), msg=task_id)

    def test_annotation_schema_types_and_enums(self):
        for task_id, ann in self.annotations.items():
            self.assertIn(ann["layer"], {"A", "B", "C"}, msg=task_id)
            self.assertIn(ann["refusal_policy"], REFUSAL_POLICIES, msg=task_id)
            self.assertIsInstance(ann["required_facts"], list, msg=task_id)
            self.assertTrue(ann["required_facts"], msg=task_id)
            self.assertTrue(all(isinstance(fact, str) and fact.strip() for fact in ann["required_facts"]), msg=task_id)
            self.assertIsInstance(ann["confirmation_rules"], list, msg=task_id)
            self.assertIsInstance(ann["expected_field_diffs"], list, msg=task_id)
            self.assertTrue(all(isinstance(diff, str) and diff.strip() for diff in ann["expected_field_diffs"]), msg=task_id)
            for rule in ann["confirmation_rules"]:
                self.assertIsInstance(rule["mutation_tool"], str, msg=task_id)
                self.assertIs(type(rule["confirmation_required"]), bool, msg=task_id)
            if "prohibited_mutations" in ann:
                self.assertIsInstance(ann["prohibited_mutations"], list, msg=task_id)
                self.assertTrue(all(isinstance(tool, str) and tool.strip() for tool in ann["prohibited_mutations"]), msg=task_id)
            if "prohibited_tools" in ann:
                self.assertIsInstance(ann["prohibited_tools"], list, msg=task_id)
                self.assertTrue(all(isinstance(tool, str) and tool.strip() for tool in ann["prohibited_tools"]), msg=task_id)
            if "privacy_rules" in ann:
                self.assertIsInstance(ann["privacy_rules"], list, msg=task_id)
                self.assertTrue(ann["privacy_rules"], msg=task_id)
                for rule in ann["privacy_rules"]:
                    self.assertIsInstance(rule["protected_fields"], list, msg=task_id)
                    self.assertTrue(rule["protected_fields"], msg=task_id)
                    self.assertTrue(all(isinstance(field, str) and field.strip() for field in rule["protected_fields"]), msg=task_id)
                    qualifiers = {key: value for key, value in rule.items() if key != "protected_fields"}
                    self.assertTrue(qualifiers, msg=task_id)
                    self.assertTrue(all(isinstance(value, bool) for value in qualifiers.values()), msg=task_id)
            if "unsafe_rules" in ann:
                self.assertIsInstance(ann["unsafe_rules"], list, msg=task_id)
                self.assertTrue(ann["unsafe_rules"], msg=task_id)
                for rule in ann["unsafe_rules"]:
                    self.assertIsInstance(rule["unsafe_action"], str, msg=task_id)
                    self.assertIs(type(rule["must_refuse"]), bool, msg=task_id)

    def test_layer_b_annotations_require_confirmation(self):
        for task_id, task in self.task_by_id.items():
            ann = self.annotations[task_id]
            if task["layer"] == "B":
                self.assertTrue(ann.get("confirmation_rules"), msg=task_id)
                self.assertTrue(ann.get("expected_field_diffs"), msg=task_id)
                self.assertEqual(ann.get("refusal_policy"), "benign_task_must_not_refuse", msg=task_id)
                mutation_tools = set(task["mutation_tools"])
                confirmed_tools = {rule["mutation_tool"] for rule in ann["confirmation_rules"]}
                self.assertEqual(confirmed_tools, mutation_tools, msg=task_id)
                self.assertEqual(self._confirmation_scope_set(self.user_policy_by_id[task_id]), mutation_tools, msg=task_id)

    def test_layer_c_annotations_define_refusal_basis(self):
        for task_id, task in self.task_by_id.items():
            ann = self.annotations[task_id]
            if task["layer"] == "C":
                self.assertTrue(ann.get("correct_refusal_if"), msg=task_id)
                self.assertIn("must_refuse", ann.get("refusal_policy", ""), msg=task_id)
                has_boundary_basis = any(
                    ann.get(key)
                    for key in ("prohibited_mutations", "privacy_rules", "unsafe_rules")
                )
                self.assertTrue(has_boundary_basis, msg=task_id)

    def test_refusal_privacy_unsafe_expected_behavior_consistency(self):
        for task_id, task in self.task_by_id.items():
            ann = self.annotations[task_id]
            refusal_policy = ann.get("refusal_policy", "")
            if task["requires_refusal"]:
                self.assertIn("must_refuse", refusal_policy, msg=task_id)
                self.assertIn(task["expected_behavior"], {"safe_boundary", "privacy_protection", "correct_refusal"}, msg=task_id)
            else:
                self.assertEqual(refusal_policy, "benign_task_must_not_refuse", msg=task_id)
                self.assertNotIn("must_refuse", refusal_policy, msg=task_id)
            if task["privacy_sensitive"]:
                self.assertTrue(ann.get("privacy_rules"), msg=task_id)
            if task["unsafe_request"]:
                self.assertTrue(ann.get("unsafe_rules"), msg=task_id)
                self.assertIn("must_refuse", refusal_policy, msg=task_id)
            if task["expected_behavior"] == "confirm_then_mutate":
                self.assertTrue(task["requires_confirmation"], msg=task_id)
                self.assertFalse(task["requires_refusal"], msg=task_id)
            if task["expected_behavior"] == "complete_benign":
                self.assertFalse(task["requires_refusal"], msg=task_id)

    def test_prohibited_tool_sets_are_cross_file_consistent(self):
        for task_id, task in self.task_by_id.items():
            task_set = set(task.get("prohibited_tools") or [])
            ann_set = set(self.annotations[task_id].get("prohibited_mutations") or [])
            ann_alias_set = set(self.annotations[task_id].get("prohibited_tools") or [])
            policy_set = set(self.user_policy_by_id[task_id].get("never_authorize_tools") or [])
            if task["requires_refusal"]:
                self.assertEqual(task_set, ann_set, msg=task_id)
                self.assertEqual(task_set, ann_alias_set, msg=task_id)
                self.assertEqual(task_set, policy_set, msg=task_id)
            else:
                self.assertEqual(task_set, set(), msg=task_id)
                self.assertEqual(ann_set, set(), msg=task_id)
                self.assertEqual(ann_alias_set, set(), msg=task_id)
                self.assertEqual(policy_set, set(), msg=task_id)

    def test_layer_c_continuation_expectation_is_explicit(self):
        for task_id, task in self.task_by_id.items():
            ann = self.annotations[task_id]
            if task["layer"] == "C":
                self.assertIn("continued_task_after_boundary_expected", ann, msg=task_id)
                self.assertIs(type(ann["continued_task_after_boundary_expected"]), bool, msg=task_id)

    def test_hybrid_boundary_tasks_define_continuation_expectation(self):
        for task_id, task in self.task_by_id.items():
            ann = self.annotations[task_id]
            if task["requires_refusal"] and task["mutation_tools"]:
                allowed = set(ann.get("allowed_mutations_after_boundary") or [])
                refused = set(ann.get("must_refuse_only") or [])
                self.assertTrue(ann.get("must_continue_allowed_subtask"), msg=task_id)
                self.assertTrue(ann.get("continued_task_after_boundary_expected"), msg=task_id)
                self.assertEqual(allowed, set(task["mutation_tools"]), msg=task_id)
                self.assertEqual(refused, set(task.get("prohibited_tools") or []), msg=task_id)
                self.assertFalse(allowed.intersection(refused), msg=task_id)
            elif task["layer"] == "C":
                self.assertFalse(ann.get("continued_task_after_boundary_expected"), msg=task_id)

    @staticmethod
    def _confirmation_scope_set(policy):
        scope = policy.get("confirmation_scope", "")
        if isinstance(scope, str):
            return {item.strip() for item in scope.split(",") if item.strip()}
        return set(scope or [])

    def test_primary_and_new_r6_metrics_are_declared(self):
        metric_targets = load_yaml(ANNOTATIONS_PATH)["metric_targets"]
        for metric in [
            "final_state_correct",
            "policy_failure_any",
            "confirmation_before_action_rate",
            "unsafe_compliance_or_privacy_violation",
            "tool_sequence_norm_distance_to_neutral",
        ]:
            self.assertIn(metric, metric_targets["primary"])
        for metric in [
            "field_level_db_diff",
            "agent_side_abandonment",
            "privacy_violation",
            "unsafe_compliance",
            "correct_refusal",
            "over_refusal",
            "continued_task_after_boundary",
        ]:
            self.assertIn(metric, metric_targets["new_r6_metrics"])


if __name__ == "__main__":
    unittest.main()
