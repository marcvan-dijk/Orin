import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from implementations.python.codegen import password_reset_rate_limit as runner


STANDARD_RESPONSE = "standard-confirmation"


def _case(requests, messages, addresses=None):
    return {
        "id": "generated-runtime-regression",
        "given": {"existingAddresses": ["a@x", "b@x"] if addresses is None else addresses},
        "when": {"requests": [
            {"email": email, "origin": origin, "at": at}
            for email, origin, at in requests
        ]},
        "then": {
            policy_id: {
                "responses": [STANDARD_RESPONSE] * len(requests),
                "resetMessages": messages[policy_id],
                "accountExistenceDisclosed": [False] * len(requests),
            }
            for policy_id in runner.POLICIES
        },
    }


class PasswordResetRateLimitTests(unittest.TestCase):
    def test_every_shared_case_and_policy_matches_complete_expected_arrays(self):
        fixture = runner.load_fixture()
        actual = runner.run_fixture()
        self.assertEqual(set(actual), set(runner.POLICIES))
        count = 0
        for policy in fixture["policies"]:
            policy_id = policy["id"]
            self.assertEqual(set(actual[policy_id]), {case["id"] for case in fixture["cases"]})
            for case in fixture["cases"]:
                with self.subTest(policy=policy_id, case=case["id"]):
                    self.assertEqual(actual[policy_id][case["id"]], case["then"][policy_id])
                    for values in actual[policy_id][case["id"]].values():
                        self.assertEqual(len(values), len(case["when"]["requests"]))
                    count += 1
        self.assertEqual(count, len(runner.POLICIES) * len(fixture["cases"]))
        self.assertGreater(count, 0)

    def test_threshold_origin_address_and_window_boundaries(self):
        five, three = runner.POLICIES
        case = _case(
            [("a@x", "one", 0)] * 6
            + [("a@x", "two", 0), ("b@x", "one", 0),
               ("a@x", "one", 899), ("a@x", "one", 900),
               ("a@x", "one", 3599), ("a@x", "one", 3600)],
            {
                five: ["sent"] * 5 + ["not-sent", "sent", "sent", "not-sent",
                                      "sent", "sent", "sent"],
                three: ["sent"] * 3 + ["not-sent"] * 4 + ["sent"]
                + ["not-sent"] * 3 + ["sent"],
            },
        )
        for policy_id in runner.POLICIES:
            with self.subTest(policy=policy_id):
                self.assertEqual(runner.run_case(policy_id, case), case["then"][policy_id])

    def test_unknown_accounts_and_repeated_denials_do_not_disclose_existence(self):
        five, three = runner.POLICIES
        requests = [("a@x", "one", at) for at in [0, 0, 0, 0, 0, 1, 899, 900]]
        case = _case(requests, {
            five: ["sent"] * 5 + ["not-sent", "not-sent", "sent"],
            three: ["sent"] * 3 + ["not-sent"] * 5,
        })
        for policy_id in runner.POLICIES:
            known = runner.run_case(policy_id, case)
            self.assertEqual(known, case["then"][policy_id])
            unknown_case = deepcopy(case)
            unknown_case["given"]["existingAddresses"] = []
            unknown = runner.run_case(policy_id, unknown_case)
            self.assertEqual(unknown["resetMessages"], ["not-sent"] * len(requests))
            self.assertEqual(unknown["responses"], known["responses"])
            self.assertEqual(unknown["accountExistenceDisclosed"], [False] * len(requests))

    def test_run_case_uses_real_decision_agent_and_generator(self):
        case = _case([("a@x", "one", 0)], {
            policy_id: ["sent"] for policy_id in runner.POLICIES
        })
        with patch.object(runner.OrinDecisionAgent, "apply_decision",
                          autospec=True, side_effect=runner.OrinDecisionAgent.apply_decision) as decide:
            with patch.object(runner, "generate_source", wraps=runner.generate_source) as generate:
                actual = runner.run_case(runner.POLICIES[0], case)
        self.assertEqual(actual, case["then"][runner.POLICIES[0]])
        self.assertEqual(decide.call_count, 1)
        self.assertEqual(decide.call_args.args[1:], (runner.MODEL, runner.UNCERTAINTY, runner.POLICIES[0]))
        generate.assert_called_once()

    def test_missing_fixture_is_an_error_not_a_skip(self):
        with self.assertRaises(FileNotFoundError):
            runner.run_fixture(runner.FIXTURE.parent / "missing-rate-limit-fixture.json")

    def test_unsupported_policy_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unsupported.*policy"):
            runner.run_case("defer", {})

    def test_malformed_fixtures_are_refused(self):
        fixture = runner.load_fixture()
        mutations = [
            lambda value: value.update(fixtureVersion="9.0"),
            lambda value: value.update(uncertainty="other"),
            lambda value: value.update(policies=[]),
            lambda value: value["policies"].append(value["policies"][0]),
            lambda value: value["policies"][0].update(id="unsupported"),
            lambda value: value.update(cases=[]),
            lambda value: value["cases"].append(value["cases"][0]),
            lambda value: value["cases"][0]["when"].update(requests=[]),
            lambda value: value["cases"][0]["when"]["requests"][0].update(at=True),
            lambda value: value["cases"][0]["when"]["requests"][0].update(at=0.5),
            lambda value: value["cases"][0]["then"].pop(runner.POLICIES[0]),
            lambda value: value["cases"][0]["then"][runner.POLICIES[0]]["responses"].pop(),
            lambda value: value["cases"][0]["then"][runner.POLICIES[0]][
                "accountExistenceDisclosed"].__setitem__(0, 0),
        ]
        for mutate in mutations:
            invalid = deepcopy(fixture)
            mutate(invalid)
            with self.subTest(mutation=mutations.index(mutate)):
                with patch.object(runner.Path, "read_text", return_value=json.dumps(invalid)):
                    with self.assertRaises(ValueError):
                        runner.load_fixture()

    def test_wrong_expected_result_is_not_silently_ignored(self):
        fixture = runner.load_fixture()
        expected = fixture["cases"][0]["then"][runner.POLICIES[0]]
        expected["responses"][0] = "incorrect expectation"
        with patch.object(runner, "load_fixture", return_value=fixture):
            with self.assertRaises(AssertionError):
                runner.run_fixture()


if __name__ == "__main__":
    unittest.main()
