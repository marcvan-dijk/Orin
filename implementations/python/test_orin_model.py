import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from orin_model import SemanticModel
from password_reset import AccountStore, CapabilityDenied, EmailProvider, PasswordResetRuntime, TokenRejected
from orin_parser import OrinParser, analyze
from lowering import lower
from conformance_runner import execute_case, expected_case_result, load_cases


FIXTURE = Path(__file__).parents[2] / "tests" / "conformance" / "password-reset.model.json"
CASES = FIXTURE.parent / "password-reset.cases.json"
TASKS_FIXTURE = FIXTURE.parent / "shared-tasks.model.json"


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
        managed["implementationPolicies"] = variants[0]["implementationPolicies"]
        existing = json.loads(json.dumps(model.document))
        existing["implementationPolicies"] = variants[1]["implementationPolicies"]

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
        document["objects"][4]["fields"][0]["type"] = "missing"

        self.assertIn("ORIN-E024", [item.code for item in SemanticModel(document).diagnostics()])

    def test_invalid_relation_and_transition_are_rejected(self):
        document = json.loads(TASKS_FIXTURE.read_text(encoding="utf-8"))
        document["objects"][7]["cardinality"] = "invalid"
        document["objects"][11]["transitions"][0]["to"] = "shared-tasks/state/missing"

        codes = [item.code for item in SemanticModel(document).diagnostics()]

        self.assertIn("ORIN-E027", codes)
        self.assertIn("ORIN-E034", codes)

    def test_shared_tasks_source_maps_to_valid_semantic_model(self):
        source = Path(__file__).parents[2] / "examples" / "shared-tasks.orin"
        model = OrinParser().parse_file(source)

        self.assertEqual(model.compilation_status(), "eligible")
        self.assertEqual(model.document["objects"][4]["kind"], "entity-type")
        workflow = next(item for item in model.document["objects"] if item["kind"] == "workflow" and item["name"] == "complete-task")
        self.assertEqual(workflow["inputs"][0]["type"], "shared-tasks/entity-type/person")
        self.assertEqual(workflow["transitions"][0]["to"], "shared-tasks/state/completed")


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
        model = OrinParser().parse_file(Path(__file__).parents[2] / "examples" / "password-reset.orin")

        self.assertEqual(model.document["module"]["imports"], ["account-store", "email-provider"])
        self.assertEqual(model.document["objects"][0]["source"]["line"], 19)
        self.assertEqual(model.document["module"]["context"]["risk"], "Account enumeration and reset-token abuse")
        self.assertEqual(model.document["module"]["implementationPolicies"]["optimize-for"], "low-latency")
        self.assertEqual(model.document["module"]["implementationPolicies"]["deploy-to"], "existing-infrastructure")

    def test_source_analysis_reports_only_rate_limit_blocker(self):
        diagnostics = analyze(Path(__file__).parents[2] / "examples" / "password-reset.orin")

        self.assertEqual(diagnostics[0].code, "ORIN-E041")

    def test_invalid_syntax_is_rejected(self):
        with self.assertRaises(ValueError):
            OrinParser().parse("module sample {\n unknown syntax\n}")


class GeneratedConformanceTests(unittest.TestCase):
    def test_cases_generated_from_language_neutral_fixture(self):
        model = SemanticModel.from_json_file(FIXTURE)
        fixture = load_cases(CASES)

        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                actual = execute_case(model, case)
                for key, expected in expected_case_result(case).items():
                    self.assertEqual(actual[key], expected)


if __name__ == "__main__":
    unittest.main()