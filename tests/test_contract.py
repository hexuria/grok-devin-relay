import ast
import copy
import re
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import relay_contract as contract

ROOT = Path(__file__).resolve().parents[1]
SESSION_ID = "devin-00000000000000000000000000000001"
SESSION_URL = "https://app.devin.ai/sessions/00000000000000000000000000000001"


def example(name):
    return contract.load_json(ROOT / "examples" / name)


def source_paths(pattern):
    excluded = {".venv", ".mypy_cache", "__pycache__", ".git"}
    return (
        path for path in ROOT.rglob(pattern)
        if not excluded.intersection(path.relative_to(ROOT).parts)
    )


class RequestTests(unittest.TestCase):
    def test_valid_request_examples(self):
        for name in (
            "bootstrap-devin.json",
            "connect-existing.json",
            "connect-new-persistent.json",
            "connect-new-per-task.json",
            "task-final.json",
            "task-none.json",
            "answer-approve.json",
        ):
            with self.subTest(name=name):
                contract.validate("request", example(name))

    def test_grok_bootstrap_uses_shared_schema(self):
        request = example("bootstrap-devin.json")
        request["provider"] = "grok"
        contract.validate("request", request)

    def test_version_is_not_silently_upgraded(self):
        for version in ("0", "2", 1, None):
            with self.subTest(version=version):
                request = example("task-final.json")
                request["protocol_version"] = version
                with self.assertRaises(contract.ContractError):
                    contract.validate("request", request)

    def test_task_cannot_override_transport_or_target(self):
        for key, value in (
            ("callback_url", "https://unapproved.example/"),
            ("session_url", SESSION_URL),
            ("GROK_WEBHOOK_KEY", "not-a-real-credential"),
            ("secret_ref", "adapter:grok:unapproved"),
            ("session", example("connect-existing.json")["session"]),
        ):
            with self.subTest(key=key):
                request = example("task-final.json")
                request[key] = value
                with self.assertRaises(contract.ContractError):
                    contract.validate("request", request)

    def test_operation_fields_do_not_bleed_between_messages(self):
        cases = (
            ("connect-existing.json", "response_mode", "final"),
            ("bootstrap-devin.json", "task", "run now"),
            ("task-final.json", "in_reply_to", "question-1"),
            ("answer-approve.json", "task", "run now"),
            ("answer-approve.json", "selected_option", "unrelated"),
        )
        for name, key, value in cases:
            with self.subTest(name=name, key=key):
                request = example(name)
                request[key] = value
                with self.assertRaises(contract.ContractError):
                    contract.validate("request", request)

    def test_new_session_cannot_have_existing_target(self):
        for name in ("connect-new-persistent.json", "connect-new-per-task.json"):
            with self.subTest(name=name):
                request = example(name)
                request["session"]["target"] = SESSION_ID
                with self.assertRaises(contract.ContractError):
                    contract.validate("request", request)

    def test_existing_session_requires_target(self):
        request = example("connect-existing.json")
        request["session"]["target"] = None
        with self.assertRaises(contract.ContractError):
            contract.validate("request", request)

    def test_replacement_is_explicit_and_only_for_existing_mode(self):
        request = example("connect-existing.json")
        request["session"]["if_missing"] = "create_after_owner_approval"
        contract.validate("request", request)
        request["session"]["mode"] = "new_persistent"
        request["session"]["target"] = None
        with self.assertRaises(contract.ContractError):
            contract.validate("request", request)

    def test_empty_or_whitespace_task_is_invalid(self):
        for task in ("", " ", "\n\t"):
            with self.subTest(task=repr(task)):
                request = example("task-final.json")
                request["task"] = task
                with self.assertRaises(contract.ContractError):
                    contract.validate("request", request)

    def test_control_characters_in_identifiers_are_rejected(self):
        for key in ("request_id", "repo", "bot_id"):
            with self.subTest(key=key):
                request = example("task-final.json")
                request[key] += "\n"
                with self.assertRaises(contract.ContractError):
                    contract.validate("request", request)

    def test_connect_target_schema_matches_normalizer(self):
        for target in (SESSION_ID, SESSION_URL, SESSION_URL + "/"):
            with self.subTest(target=target):
                request = example("connect-existing.json")
                request["session"]["target"] = target
                contract.validate("request", request)
                self.assertEqual(contract.normalize_session_target(target), SESSION_ID)
        request["session"]["target"] = SESSION_URL + "\n"
        with self.assertRaises(contract.ContractError):
            contract.validate("request", request)

    def test_select_answer_requires_an_option(self):
        request = example("answer-approve.json")
        request["decision"] = "select"
        with self.assertRaises(contract.ContractError):
            contract.validate("request", request)
        request["selected_option"] = "Read only"
        contract.validate("request", request)


class SessionTests(unittest.TestCase):
    def test_accepts_only_canonical_id_and_trusted_link(self):
        for target in (SESSION_ID, SESSION_URL, SESSION_URL + "/"):
            with self.subTest(target=target):
                self.assertEqual(contract.normalize_session_target(target), SESSION_ID)

    def test_rejects_unsafe_or_ambiguous_links(self):
        targets = (
            SESSION_ID.removeprefix("devin-"),
            SESSION_URL.replace("https:", "http:"),
            SESSION_URL + "?session=other",
            SESSION_URL + "#fragment",
            SESSION_URL.replace("app.devin.ai", "app.devin.ai.unapproved.example"),
            SESSION_URL.replace("app.devin.ai", "user@app.devin.ai"),
            SESSION_URL.replace("app.devin.ai", "app.devin.ai:443"),
            SESSION_URL.replace("/sessions/", "/other/"),
            SESSION_URL + "\n",
            SESSION_ID + "\n",
            " " + SESSION_ID,
            "https://[invalid",
        )
        for target in targets:
            with self.subTest(target=target):
                with self.assertRaises(contract.ContractError):
                    contract.normalize_session_target(target)


class ReportTests(unittest.TestCase):
    def test_report_examples_validate(self):
        for name in ("permission-question.json", "report-done.json"):
            with self.subTest(name=name):
                contract.validate("report", example(name))

    def test_nullable_nonapplicable_fields_remain_valid(self):
        report = example("report-done.json")
        report["repo"] = None
        contract.validate("report", report)

    def test_all_legacy_fields_are_still_required(self):
        report = example("report-done.json")
        for key in (
            "kind", "repo", "session_url", "pr", "summary", "details", "options",
            "default_if_no_answer",
        ):
            with self.subTest(key=key):
                changed = copy.deepcopy(report)
                del changed[key]
                with self.assertRaises(contract.ContractError):
                    contract.validate("report", changed)

    def test_nonquestions_have_no_options_or_decision_state(self):
        for key, value in (
            ("options", ["Approve"]), ("question_id", "q-1"),
            ("decision_type", "permission"),
        ):
            with self.subTest(key=key):
                report = example("report-done.json")
                report[key] = value
                with self.assertRaises(contract.ContractError):
                    contract.validate("report", report)

    def test_questions_need_correlation_type_and_unique_options(self):
        for key, value in (
            ("question_id", None), ("decision_type", None),
            ("options", []), ("options", ["same", "same"]),
        ):
            with self.subTest(key=key):
                report = example("permission-question.json")
                report[key] = value
                with self.assertRaises(contract.ContractError):
                    contract.validate("report", report)

    def test_permission_and_platform_approval_default_to_pause(self):
        for decision_type in ("permission", "platform_approval"):
            for default in (None, "Proceed", "Assume approval after 10 minutes"):
                with self.subTest(decision_type=decision_type, default=default):
                    report = example("permission-question.json")
                    report["decision_type"] = decision_type
                    report["default_if_no_answer"] = default
                    with self.assertRaises(contract.ContractError):
                        contract.validate("report", report)

    def test_summary_is_one_line(self):
        report = example("report-done.json")
        report["summary"] = "Done\nPending"
        with self.assertRaises(contract.ContractError):
            contract.validate("report", report)

    def test_response_mode_matrix(self):
        expected = {
            "none": {"question", "blocked"},
            "final": {"question", "blocked", "done"},
            "progress": {"question", "blocked", "done", "update"},
        }
        for mode in contract.RESPONSE_MODES:
            for kind in contract.REPORT_KINDS:
                with self.subTest(mode=mode, kind=kind):
                    self.assertEqual(contract.should_report(mode, kind), kind in expected[mode])

    def test_unknown_response_modes_or_kinds_fail_closed(self):
        for mode, kind in (("silent-approve", "done"), ("none", "task")):
            with self.subTest(mode=mode, kind=kind):
                with self.assertRaises(contract.ContractError):
                    contract.should_report(mode, kind)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.request = example("task-final.json")
        self.registry = example("registry.json")
        self.context = {
            "org_id": "org-example",
            "automation_id": "auto-example",
            "session_id": SESSION_ID,
        }

    def test_matching_context(self):
        contract.check_delivery(self.request, self.registry, **self.context)

    def test_unknown_bot_and_unapproved_repository(self):
        for key, value in (("bot_id", "unknown"), ("repo", "another/repo")):
            with self.subTest(key=key):
                request = copy.deepcopy(self.request)
                request[key] = value
                with self.assertRaises(contract.ContractError):
                    contract.check_delivery(request, self.registry, **self.context)

    def test_wrong_organization_automation_or_session(self):
        for key, value in (
            ("org_id", "org-other"), ("automation_id", "auto-other"),
            ("session_id", "devin-0123456789abcdef0123456789abcdef"),
        ):
            with self.subTest(key=key):
                context = {**self.context, key: value}
                with self.assertRaises(contract.ContractError):
                    contract.check_delivery(self.request, self.registry, **context)

    def test_new_per_task_checks_automation_not_fixed_session(self):
        bot = self.registry["bots"]["pua-review"]
        bot["session_mode"] = "new_per_task"
        bot["session_id"] = None
        self.context["session_id"] = "devin-0123456789abcdef0123456789abcdef"
        contract.check_delivery(self.request, self.registry, **self.context)
        self.context["automation_id"] = "auto-other"
        with self.assertRaises(contract.ContractError):
            contract.check_delivery(self.request, self.registry, **self.context)

    def test_new_persistent_requires_real_registered_target(self):
        bot = self.registry["bots"]["pua-review"]
        bot["session_mode"] = "new_persistent"
        bot["session_id"] = None
        with self.assertRaises(contract.ContractError):
            contract.check_delivery(self.request, self.registry, **self.context)
        bot["session_id"] = SESSION_ID
        contract.check_delivery(self.request, self.registry, **self.context)

    def test_per_task_inbox_must_not_launch_a_new_session_for_an_answer(self):
        bot = self.registry["bots"]["pua-review"]
        bot["session_mode"] = "new_per_task"
        bot["session_id"] = None
        with self.assertRaisesRegex(contract.ContractError, "original-session transport"):
            contract.check_delivery(
                example("answer-approve.json"), self.registry, **self.context
            )

    def test_management_operations_require_control_plane(self):
        for name in ("connect-existing.json", "bootstrap-devin.json"):
            with self.subTest(name=name):
                with self.assertRaises(contract.ContractError):
                    contract.check_delivery(example(name), self.registry, **self.context)


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.answer = example("answer-approve.json")
        self.pending = example("permission-question.json")

    def check(self, **changes):
        context = {"current_session_id": SESSION_ID, "question_open": True, **changes}
        contract.check_answer(self.answer, self.pending, **context)

    def test_permission_correlation(self):
        self.check()
        self.answer["decision"] = "deny"
        self.check()

    def test_wrong_bot_repo_or_question_is_rejected(self):
        for key, value in (
            ("bot_id", "other"), ("repo", "another/repo"),
            ("in_reply_to", "unrelated"),
        ):
            with self.subTest(key=key):
                answer = copy.deepcopy(self.answer)
                answer[key] = value
                with self.assertRaises(contract.ContractError):
                    contract.check_answer(
                        answer, self.pending, current_session_id=SESSION_ID,
                        question_open=True,
                    )

    def test_answer_goes_to_original_session(self):
        with self.assertRaises(contract.ContractError):
            self.check(current_session_id="devin-0123456789abcdef0123456789abcdef")

    def test_closed_question_or_nonquestion_is_rejected(self):
        with self.assertRaises(contract.ContractError):
            self.check(question_open=False)
        self.pending = example("report-done.json")
        with self.assertRaises(contract.ContractError):
            self.check()

    def test_chat_approval_cannot_satisfy_platform_gate(self):
        self.pending["decision_type"] = "platform_approval"
        with self.assertRaisesRegex(contract.ContractError, "Native platform approval"):
            self.check()
        self.answer["decision"] = "deny"
        self.check()

    def test_clarification_requires_exact_offered_selection(self):
        self.pending["decision_type"] = "clarification"
        with self.assertRaises(contract.ContractError):
            self.check()
        self.answer["decision"] = "select"
        self.answer["selected_option"] = "Not offered"
        with self.assertRaises(contract.ContractError):
            self.check()
        self.answer["selected_option"] = self.pending["options"][0]
        self.check()

    def test_select_does_not_approve_permission(self):
        self.answer["decision"] = "select"
        self.answer["selected_option"] = self.pending["options"][0]
        with self.assertRaises(contract.ContractError):
            self.check()


class RegistryTests(unittest.TestCase):
    def test_synthetic_registry(self):
        contract.validate("registry", example("registry.json"))

    def test_raw_credentials_and_urls_are_not_secret_references(self):
        for value in ("Bearer redacted", "https://unapproved.example/", "plain-key"):
            with self.subTest(value=value):
                registry = example("registry.json")
                registry["bots"]["pua-review"]["inbox_key_secret_ref"] = value
                with self.assertRaises(contract.ContractError):
                    contract.validate("registry", registry)

    def test_mode_specific_session_state(self):
        for mode, session_id in (("existing", None), ("new_per_task", SESSION_ID)):
            with self.subTest(mode=mode):
                registry = example("registry.json")
                bot = registry["bots"]["pua-review"]
                bot["session_mode"] = mode
                bot["session_id"] = session_id
                with self.assertRaises(contract.ContractError):
                    contract.validate("registry", registry)

    def test_registry_cannot_enroll_no_repositories(self):
        registry = example("registry.json")
        registry["bots"]["pua-review"]["allowed_repos"] = []
        with self.assertRaises(contract.ContractError):
            contract.validate("registry", registry)


class PackageTests(unittest.TestCase):
    def test_schema_documents_are_valid_and_local(self):
        for kind in contract.SCHEMA_KINDS:
            with self.subTest(kind=kind):
                contract.validator(kind)
        with self.assertRaises(contract.ContractError):
            contract._check_local_refs({"$ref": "https://unapproved.example/schema"})

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"request_id":"one","request_id":"two"}', encoding="utf-8")
            with self.assertRaises(contract.ContractError):
                contract.load_json(path)

    def test_nonfinite_json_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for value in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(value=value):
                    path.write_text('{"value":' + value + "}", encoding="utf-8")
                    with self.assertRaises(contract.ContractError):
                        contract.load_json(path)

    def test_invalid_payload_errors_do_not_echo_values(self):
        request = example("task-final.json")
        sentinel = "SENSITIVE-SENTINEL-NOT-A-KEY"
        request["unknown"] = sentinel
        with self.assertRaises(contract.ContractError) as caught:
            contract.validate("request", request)
        self.assertNotIn(sentinel, str(caught.exception))

    def test_only_synthetic_session_ids_in_repo(self):
        allowed = {
            "devin-00000000000000000000000000000001",
            "devin-0123456789abcdef0123456789abcdef",
        }
        for pattern in ("*.md", "*.json", "*.py"):
            for path in source_paths(pattern):
                content = path.read_text(encoding="utf-8")
                for found in re.findall(r"devin-[0-9a-f]{32}", content):
                    with self.subTest(path=str(path.relative_to(ROOT)), found=found):
                        self.assertIn(found, allowed)

    def test_manifest_and_only_devin_root_skills(self):
        manifest = contract.load_json(ROOT / ".devin-plugin" / "plugin.json")
        self.assertEqual(manifest["name"], "grok-devin-relay")
        expected = {
            "relay-install", "relay-bootstrap-devin", "relay-connect-session",
            "relay-message", "grok-relay-report",
        }
        paths = list((ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual({path.parent.name for path in paths}, expected)
        self.assertTrue((ROOT / "providers" / "grok" / "SKILL.md").is_file())
        for path in paths:
            with self.subTest(path=path.name):
                self.assertIn("Use only in Devin.", path.read_text(encoding="utf-8"))

    def test_skill_frontmatter_and_local_markdown_links(self):
        for path in source_paths("*.md"):
            with self.subTest(path=str(path.relative_to(ROOT))):
                content = path.read_text(encoding="utf-8")
                if path.name == "SKILL.md":
                    self.assertTrue(content.startswith("---\n"))
                    frontmatter = yaml.safe_load(content.split("---", 2)[1])
                    self.assertRegex(frontmatter["name"], r"^[a-z0-9-]+$")
                    self.assertIsInstance(frontmatter["description"], str)
                for target in re.findall(r"\]\(([^)]+)\)", content):
                    if not target.startswith(("https://", "#")):
                        self.assertTrue((path.parent / target).is_file(), target)

    def test_automation_examples_are_disabled_and_have_restricted_egress(self):
        for path in (ROOT / "examples").glob("automation-*.json"):
            with self.subTest(path=path.name):
                config = contract.load_json(path)
                self.assertFalse(config["enabled"])
                self.assertEqual(config["triggers"], [
                    {"event_type": "webhook:incoming", "replies": []}
                ])
                self.assertEqual(config["tools"]["mcp_servers"], [])
                self.assertEqual(config["run_as"], {"type": "creator"})
                hosts = config["session_settings"]["net_policy"]["allow"]
                self.assertEqual(hosts, [
                    {"hostname": "git-manager.devin.ai"},
                    {"hostname": "relay.example.com"},
                ])
                self.assertIn("EXAMPLE ONLY", config["actions"][0]["prompt"])

    def test_offline_helper_has_no_transport_imports(self):
        tree = ast.parse((ROOT / "scripts" / "relay_contract.py").read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module)
        self.assertTrue(imports.isdisjoint({
            "requests", "httpx", "socket", "urllib.request", "subprocess"
        }))

    def test_every_json_file_is_parseable(self):
        for path in source_paths("*.json"):
            with self.subTest(path=str(path.relative_to(ROOT))):
                contract.load_json(path)


if __name__ == "__main__":
    unittest.main()
