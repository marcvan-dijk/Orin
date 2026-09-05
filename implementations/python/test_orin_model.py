import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from orin_model import SemanticModel
from password_reset import AccountStore, CapabilityDenied, EmailProvider, PasswordResetRuntime, TokenRejected
from orin_parser import OrinParser, analyze
from orin_structured_frontend import StructuredOrinFrontend
from lowering import lower
from password_reset_proof import run_derivation_proof
from conformance_runner import execute_case, expected_case_result, load_cases


FIXTURE = Path(__file__).parents[2] / "tests" / "conformance" / "password-reset.model.json"
CASES = FIXTURE.parent / "password-reset.cases.json"
TASKS_FIXTURE = FIXTURE.parent / "shared-tasks.model.json"
PASSWORD_RESET_STRUCTURED = FIXTURE.parent / "password-reset.structured.json"
TASKS_STRUCTURED = FIXTURE.parent / "shared-tasks.structured.json"


class SemanticModelTests(unittest.TestCase):
    def test_fixture_is_blocked_by_rate_limit(self):
        model = SemanticModel.from_json_file(FIXTURE)
        self.assertEqual(model.compilation_status(), "blocked")
        self.assertEqual([item.code for item in model.diagnostics()], ["ORIN-E041"])

    def test_canonicalization_ignores_order(self):
        model = SemanticModel.from_json_file(FIXTURE)
        shuffled = json.loads(json.dumps(model.document))
        shuffled["objects"].reverse()
        self.assertEqual(model.canonical(), SemanticModel(shuffled).canonical())

    def test_canonicalization_ignores_source_locations(self):
        model = SemanticModel.from_json_file(FIXTURE)
        changed = json.loads(json.dumps(model.document))
        changed["objects"][0]["source"] = {"line": 999}
        self.assertEqual(model.canonical(), SemanticModel(changed).canonical())

    def test_implementation_policies_do_not_change_semantic_model(self):
        model = SemanticModel.from_json_file(FIXTURE)
        policy_fixture = json.loads((FIXTURE.parent / "password-reset.policies.json").read_text(encoding="utf-8"))
        variants = policy_fixture["variants"]
        managed = json.loads(json.dumps(model.document))
        managed["module"]["implementationPolicies"] = variants[0]["implementationPolicies"]
        existing = json.loads(json.dumps(model.document))
        existing["module"]["implementationPolicies"] = variants[1]["implementationPolicies"]

        self.assertEqual(SemanticModel(managed).canonical(), SemanticModel(existing).canonical())
        self.assertNotEqual(lower(SemanticModel(managed)), lower(SemanticModel(existing)))
        self.assertTrue(policy_fixture["assertions"]["semanticBehaviorUnchanged"])
        self.assertTrue(policy_fixture["assertions"]["artifactStrategyChanges"])

    def test_unknown_reference_fails(self):
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        document["objects"][0]["requires"] = ["missing"]
        model = SemanticModel(document)
        self.assertIn("ORIN-E007", [item.code for item in model.diagnostics()])
        self.assertEqual(model.compilation_status(), "blocked")

    def test_shared_tasks_model_is_semantically_complete(self):
        model = SemanticModel.from_json_file(TASKS_FIXTURE)

        self.assertEqual(model.diagnostics(), [])
        self.assertEqual(model.compilation_status(), "eligible")

    def test_entity_requires_typed_identity_field(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        person = next(item for item in document["objects"] if item["id"] == "shared-tasks/entity-type/person")
        person["fields"][0]["type"] = "missing"

        self.assertIn("ORIN-E024", [item.code for item in SemanticModel(document).diagnostics()])

    def test_invalid_relation_and_transition_are_rejected(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        relation = next(item for item in document["objects"] if item["id"] == "shared-tasks/relation/member-of")
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        relation["cardinality"] = "invalid"
        workflow["transitions"][0]["to"] = "shared-tasks/state/missing"

        codes = [item.code for item in SemanticModel(document).diagnostics()]

        self.assertIn("ORIN-E027", codes)
        self.assertIn("ORIN-E034", codes)

    def test_workflow_actor_capability_bindings_and_effect_durability_are_required(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        effect = next(item for item in document["objects"] if item["id"] == "shared-tasks/effect/persistent-entity-store.write.task-state")

        workflow["actorCapabilities"] = [
            {"actor": "actor", "capability": "shared-tasks/capability/complete-task"}
        ]
        effect.pop("durability", None)
        effect["requires"] = ["shared-tasks/capability/write-task-state"]

        codes = [item.code for item in SemanticModel(document).diagnostics()]

        self.assertIn("ORIN-E037", codes)
        self.assertIn("ORIN-E039", codes)

    def test_actor_capability_bindings_require_actor_declaration(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        workflow.pop("actor", None)

        codes = [item.code for item in SemanticModel(document).diagnostics()]

        self.assertIn("ORIN-E038", codes)

    def test_actor_contract_diagnostics_do_not_hide_other_workflow_diagnostics(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        workflow["actorCapabilities"] = "invalid"
        workflow["transitions"][0]["to"] = "shared-tasks/state/missing"

        codes = [item.code for item in SemanticModel(document).diagnostics()]

        self.assertIn("ORIN-E038", codes)
        self.assertIn("ORIN-E034", codes)

    def test_actor_capability_shape_and_actor_requirement_diagnostics_both_emit(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        workflow.pop("actor", None)
        workflow["actorCapabilities"] = "invalid"

        diagnostics = SemanticModel(document).diagnostics()
        messages = [item.message for item in diagnostics if item.code == "ORIN-E038"]

        self.assertIn("workflow actorCapabilities must be a list", messages)
        self.assertIn("workflow actorCapabilities require actor declaration", messages)

    def test_actor_capability_entries_must_be_well_formed(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        workflow["actorCapabilities"] = ["invalid"]

        diagnostics = SemanticModel(document).diagnostics()
        messages = [item.message for item in diagnostics if item.code == "ORIN-E038"]

        self.assertIn("workflow actorCapabilities entries must be objects", messages)

    def test_actor_capability_entries_must_match_declared_workflow_actor(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        workflow["actorCapabilities"].append({"actor": "task", "capability": "shared-tasks/capability/complete-task"})

        messages = [item.message for item in SemanticModel(document).diagnostics() if item.code == "ORIN-E038"]

        self.assertIn("workflow actorCapabilities actor must match workflow actor: task", messages)

    def test_actor_capability_contract_is_required_for_actor_scoped_workflow(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        workflow.pop("actorCapabilities", None)

        messages = [item.message for item in SemanticModel(document).diagnostics() if item.code == "ORIN-E038"]

        self.assertIn("workflow actor requires actorCapabilities contract for required capabilities/effects", messages)

    def test_missing_actor_input_still_emits_missing_contract_diagnostic(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        workflow.pop("actorCapabilities", None)
        workflow["actor"] = "missing-actor"

        messages = [item.message for item in SemanticModel(document).diagnostics() if item.code == "ORIN-E038"]

        self.assertIn("workflow actor must reference a declared input: missing-actor", messages)
        self.assertIn("workflow actor requires actorCapabilities contract for required capabilities/effects", messages)

    def test_actor_must_be_string_input_name(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        workflow = next(item for item in document["objects"] if item["id"] == "shared-tasks/workflow/complete-task")
        workflow["actor"] = {"name": "actor"}

        messages = [item.message for item in SemanticModel(document).diagnostics() if item.code == "ORIN-E038"]

        self.assertIn("workflow actor must be a string input name", messages)

    def test_orphaned_effect_is_reported_by_readiness_diagnostics(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        document["objects"].append({
            "id": "shared-tasks/effect/persistent-entity-store.write.audit-log",
            "kind": "effect",
            "name": "persistent-entity-store.write.audit-log",
            "status": "accepted",
            "requires": ["shared-tasks/capability/write-task-state"],
            "durability": "strong",
        })

        model = SemanticModel(document)
        self.assertIn("ORIN-E042", [item.code for item in model.diagnostics()])
        self.assertEqual(model.compilation_status(), "fail")

    def test_orphaned_capability_is_reported_by_readiness_diagnostics(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        document["objects"].append({
            "id": "shared-tasks/capability/archive-task",
            "kind": "capability",
            "name": "archive-task",
            "status": "accepted",
        })

        model = SemanticModel(document)
        self.assertIn("ORIN-E043", [item.code for item in model.diagnostics()])
        self.assertEqual(model.compilation_status(), "fail")

    def test_orphaned_state_is_reported_by_readiness_diagnostics(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        document["objects"].append({
            "id": "shared-tasks/state/archived",
            "kind": "state",
            "name": "archived",
            "status": "accepted",
        })

        model = SemanticModel(document)
        self.assertIn("ORIN-E044", [item.code for item in model.diagnostics()])
        self.assertEqual(model.compilation_status(), "fail")

    def test_shared_tasks_source_maps_to_valid_semantic_model(self):
        source = Path(__file__).parents[2] / "examples" / "shared-tasks.orin"
        model = OrinParser().parse_file(source)

        self.assertEqual(model.compilation_status(), "eligible")
        self.assertEqual(next(item for item in model.document["objects"] if item["name"] == "person")["kind"], "entity-type")
        workflow = next(item for item in model.document["objects"] if item["kind"] == "workflow" and item["name"] == "complete-task")
        effect = next(
            item for item in model.document["objects"]
            if item["kind"] == "effect" and item["name"] == "persistent-entity-store.write.task-state"
        )
        self.assertEqual(workflow["inputs"][0]["type"], "shared-tasks/entity-type/person")
        self.assertEqual(workflow["transitions"][0]["to"], "shared-tasks/state/completed")
        self.assertEqual(workflow["uses"], ["shared-tasks/effect/persistent-entity-store.write.task-state"])
        self.assertEqual(workflow["actorCapabilities"][1]["capability"], "shared-tasks/capability/write-task-state")
        self.assertEqual(effect["durability"], "strong")


class PasswordResetRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.email_provider = EmailProvider()
        self.runtime = PasswordResetRuntime(AccountStore({"person@example.com"}), self.email_provider)

    def test_registered_address_sends_message_and_hides_existence(self):
        result = self.runtime.request_reset("person@example.com", {"person.request-password-reset", "system.send-reset-message"})

        self.assertEqual(result.reset_message, "sent")
        self.assertFalse(result.account_existence_disclosed)
        self.assertEqual(self.email_provider.sent_messages, ["person@example.com"])
        self.assertEqual(result.inputs["email"], "person@example.com")
        self.assertEqual(result.decisions["send_message"], True)
        self.assertIn("reset-token-issued", result.state_changes)
        self.assertIn("email-provider.send-reset-message", result.effects)
        self.assertEqual(result.outputs["response"], "standard-confirmation")
        self.assertEqual(result.failures, ())

    def test_unknown_address_returns_same_response_without_message(self):
        result = self.runtime.request_reset("unknown@example.com", {"person.request-password-reset"})

        self.assertEqual(result.response, "standard-confirmation")
        self.assertEqual(result.reset_message, "not-sent")
        self.assertFalse(result.account_existence_disclosed)

    def test_delivery_failure_does_not_disclose_account(self):
        self.email_provider.available = False

        result = self.runtime.request_reset("person@example.com", {"person.request-password-reset", "system.send-reset-message"})

        self.assertEqual(result.recovery, "no-account-state-disclosed")
        self.assertFalse(result.account_existence_disclosed)

    def test_account_store_failure_does_not_disclose_account(self):
        self.runtime.account_store.available = False

        result = self.runtime.request_reset("person@example.com", {"person.request-password-reset"})

        self.assertEqual(result.recovery, "no-account-state-disclosed")
        self.assertFalse(result.account_existence_disclosed)
        self.assertEqual(result.decisions["account_exists"], "unknown")
        self.assertEqual(result.failures, ("account-store.unavailable",))

    def test_token_expires_after_fifteen_minutes(self):
        result = self.runtime.request_reset("person@example.com", {"person.request-password-reset", "system.send-reset-message"}, now=100)

        with self.assertRaisesRegex(TokenRejected, "expired"):
            self.runtime.redeem_reset(result.reset_token, now=100 + 15 * 60)

    def test_token_is_single_use(self):
        result = self.runtime.request_reset("person@example.com", {"person.request-password-reset", "system.send-reset-message"})

        self.assertEqual(self.runtime.redeem_reset(result.reset_token, now=1), "person@example.com")
        with self.assertRaisesRegex(TokenRejected, "already used"):
            self.runtime.redeem_reset(result.reset_token, now=2)

    def test_repeated_requests_issue_distinct_tokens(self):
        capabilities = {"person.request-password-reset", "system.send-reset-message"}
        first = self.runtime.request_reset("person@example.com", capabilities)
        second = self.runtime.request_reset("person@example.com", capabilities)

        self.assertNotEqual(first.reset_token, second.reset_token)
        self.assertEqual(len(self.email_provider.sent_messages), 2)

    def test_missing_capability_is_rejected(self):
        with self.assertRaises(CapabilityDenied):
            self.runtime.request_reset("person@example.com", set())


class OrinParserTests(unittest.TestCase):
    def test_password_reset_source_produces_model_and_blocks_rate_limit(self):
        model = OrinParser().parse_file(Path(__file__).parents[2] / "examples" / "password-reset.orin")

        self.assertEqual(model.document["module"]["id"], "account.password-reset/module")
        self.assertEqual(model.compilation_status(), "blocked")
        self.assertEqual(len(analyze(Path(__file__).parents[2] / "examples" / "password-reset.orin")), 1)

    def test_parser_preserves_imports_and_source_locations(self):
        source_path = Path(__file__).parents[2] / "examples" / "password-reset.orin"
        model = OrinParser().parse_file(source_path)
        expected_type_line = next(
            index for index, line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), 1) if line.strip() == "type email"
        )

        self.assertEqual(model.document["module"]["imports"], ["account-store", "email-provider"])
        self.assertEqual(model.document["objects"][0]["source"]["line"], expected_type_line)
        self.assertEqual(model.document["module"]["context"]["risk"], "Account enumeration and reset-token abuse")
        self.assertEqual(model.document["module"]["implementationPolicies"]["optimize-for"], "low-latency")
        self.assertEqual(model.document["module"]["implementationPolicies"]["deploy-to"], "existing-infrastructure")

    def test_source_analysis_reports_only_rate_limit_blocker(self):
        diagnostics = analyze(Path(__file__).parents[2] / "examples" / "password-reset.orin")

        self.assertEqual(diagnostics[0].code, "ORIN-E041")

    def test_invalid_syntax_is_rejected(self):
        with self.assertRaises(ValueError):
            OrinParser().parse("module sample {\n unknown syntax\n}")


class FrontendEquivalenceTests(unittest.TestCase):
    def test_password_reset_text_and_structured_frontends_are_equivalent(self):
        orin_model = OrinParser().parse_file(Path(__file__).parents[2] / "examples" / "password-reset.orin")
        structured_model = StructuredOrinFrontend().parse_file(PASSWORD_RESET_STRUCTURED)

        self.assertEqual(orin_model.canonical(), structured_model.canonical())

    def test_shared_tasks_text_and_structured_frontends_are_equivalent(self):
        orin_model = OrinParser().parse_file(Path(__file__).parents[2] / "examples" / "shared-tasks.orin")
        structured_model = StructuredOrinFrontend().parse_file(TASKS_STRUCTURED)

        self.assertEqual(orin_model.canonical(), structured_model.canonical())


class GeneratedConformanceTests(unittest.TestCase):
    def test_cases_generated_from_language_neutral_fixture(self):
        model = SemanticModel.from_json_file(FIXTURE)
        fixture = load_cases(CASES)

        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                actual = execute_case(model, case)
                for key, expected in expected_case_result(case).items():
                    self.assertEqual(actual[key], expected)


class PasswordResetProofRunTests(unittest.TestCase):
    def test_password_reset_end_to_end_derivation_proof(self):
        proof = run_derivation_proof()

        self.assertEqual(proof["blockedCompilation"], "blocked")
        self.assertEqual(proof["resolvedCompilation"], "eligible")
        self.assertTrue(proof["canonicalMeaningStableAcrossVariants"])
        self.assertGreaterEqual(len(proof["variants"]), 2)
        self.assertNotEqual(proof["variants"][0]["derivedArtifact"], proof["variants"][1]["derivedArtifact"])
        expected_behavior_cases = [
            case["id"]
            for case in load_cases(CASES)["cases"]
            if case.get("when", {}).get("action") != "compile"
        ]
        self.assertEqual(proof["behaviorCases"], expected_behavior_cases)


if __name__ == "__main__":
    unittest.main()