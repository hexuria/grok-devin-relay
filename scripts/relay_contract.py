"""Offline validation, not an authenticated router or approval service."""

import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft7Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SESSION_ID = re.compile(r"devin-[0-9a-f]{32}")
SESSION_PATH = re.compile(r"/sessions/([0-9a-f]{32})/?")
PLACEHOLDER = re.compile(r"\$\{([a-z_]+)\}")
PLACEHOLDER_NAMES = ("session_id", "org_id", "automation_id", "owner_id", "relay_host")
SCHEMA_KINDS = ("request", "report", "registry")
RESPONSE_MODES = ("none", "final", "progress")
REPORT_KINDS = ("update", "question", "done", "blocked")


class ContractError(ValueError):
    pass


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("Duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ContractError("Non-finite JSON number")


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContractError("Cannot read valid JSON") from error


def sample_variables() -> dict[str, str]:
    return {
        "session_id": uuid.uuid4().hex,
        "org_id": f"org-{uuid.uuid4().hex}",
        "automation_id": f"auto-{uuid.uuid4().hex}",
        "owner_id": f"user-{uuid.uuid4().hex}",
        "relay_host": "relay.example.com",
    }


def render(value: Any, variables: dict[str, str]) -> Any:
    unresolved: set[str] = set()

    def replace(child: Any) -> Any:
        if isinstance(child, dict):
            return {replace(key): replace(nested) for key, nested in child.items()}
        if isinstance(child, list):
            return [replace(nested) for nested in child]
        if isinstance(child, str):
            return PLACEHOLDER.sub(
                lambda match: variables.get(match.group(1), match.group(0)), child
            )
        return child

    rendered = replace(value)

    def find_unresolved(child: Any) -> None:
        if isinstance(child, dict):
            for key, nested in child.items():
                find_unresolved(key)
                find_unresolved(nested)
        elif isinstance(child, list):
            for nested in child:
                find_unresolved(nested)
        elif isinstance(child, str):
            unresolved.update(match.group(1) for match in PLACEHOLDER.finditer(child))

    find_unresolved(rendered)
    if unresolved:
        raise ContractError(f"Unresolved placeholder: {','.join(sorted(unresolved))}")
    return rendered


def _check_local_refs(value: Any) -> None:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if ref is not None and (not isinstance(ref, str) or not ref.startswith("#/")):
            raise ContractError("Only local schema references are allowed")
        for child in value.values():
            _check_local_refs(child)
    elif isinstance(value, list):
        for child in value:
            _check_local_refs(child)


def validator(kind: str) -> Draft7Validator:
    if kind not in SCHEMA_KINDS:
        raise ContractError("Unknown schema kind")
    schema = load_json(ROOT / "shared" / "schemas" / f"{kind}.schema.json")
    _check_local_refs(schema)
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema, format_checker=FormatChecker())


def validate(kind: str, payload: Any) -> None:
    error = next(validator(kind).iter_errors(payload), None)
    if error is not None:
        raise ContractError(f"Invalid {kind} ({error.validator})")


def normalize_session_target(target: str) -> str:
    if any(character.isspace() or ord(character) < 32 for character in target):
        raise ContractError("Invalid session target")
    if SESSION_ID.fullmatch(target):
        return target
    try:
        parsed = urlsplit(target)
    except ValueError as error:
        raise ContractError("Invalid session target") from error
    match = SESSION_PATH.fullmatch(parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "app.devin.ai"
        or parsed.query
        or parsed.fragment
        or match is None
    ):
        raise ContractError("Invalid session target")
    return f"devin-{match.group(1)}"


def should_report(response_mode: str, kind: str) -> bool:
    if response_mode not in RESPONSE_MODES or kind not in REPORT_KINDS:
        raise ContractError("Unknown response mode or report kind")
    if kind in ("question", "blocked"):
        return True
    if kind == "update":
        return response_mode == "progress"
    return response_mode != "none"


def check_delivery(
    request: dict[str, Any],
    registry: dict[str, Any],
    *,
    org_id: str,
    automation_id: str,
    session_id: str,
) -> None:
    """Check automation delivery after the host authenticates the sender."""
    validate("request", request)
    validate("registry", registry)
    if request["operation"] not in ("task", "answer"):
        raise ContractError("Management operation requires the control plane")
    bot = registry["bots"].get(request["bot_id"])
    if bot is None:
        raise ContractError("Unknown bot")
    if request["repo"] not in bot["allowed_repos"]:
        raise ContractError("Repository not enrolled")
    if bot["org_id"] != org_id or bot["automation_id"] != automation_id:
        raise ContractError("Wrong delivery context")
    if bot["session_mode"] == "new_per_task" and request["operation"] == "answer":
        raise ContractError("Answer requires an original-session transport")
    if not SESSION_ID.fullmatch(session_id):
        raise ContractError("Invalid delivered session ID")
    if bot["session_mode"] != "new_per_task" and bot["session_id"] != session_id:
        raise ContractError("Wrong or unregistered target session")


def check_answer(
    answer: dict[str, Any],
    pending_report: dict[str, Any],
    *,
    current_session_id: str,
    question_open: bool,
) -> None:
    """Check correlation only; the host must authenticate owner decisions."""
    validate("request", answer)
    validate("report", pending_report)
    if (
        answer["operation"] != "answer"
        or pending_report["kind"] != "question"
        or not question_open
    ):
        raise ContractError("No matching open question")
    if (
        answer["bot_id"] != pending_report["bot_id"]
        or answer["repo"] != pending_report["repo"]
        or answer["in_reply_to"] != pending_report["question_id"]
        or current_session_id != normalize_session_target(pending_report["session_url"])
    ):
        raise ContractError("Wrong answer correlation")
    decision_type = pending_report["decision_type"]
    if decision_type == "clarification":
        if (
            answer["decision"] != "select"
            or answer["selected_option"] not in pending_report["options"]
        ):
            raise ContractError("Answer must select an offered option")
    elif answer["decision"] not in ("approve", "deny"):
        raise ContractError("Explicit owner decision required")
    if decision_type == "platform_approval" and answer["decision"] == "approve":
        raise ContractError("Native platform approval still required")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=SCHEMA_KINDS)
    parser.add_argument("path", type=Path)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--var", action="append", default=[], metavar="NAME=VALUE")
    args = parser.parse_args(argv)
    try:
        variables = sample_variables() if args.sample else {}
        for variable in args.var:
            name, separator, value = variable.partition("=")
            if not separator:
                raise ContractError("--var must use NAME=VALUE")
            if name not in PLACEHOLDER_NAMES:
                raise ContractError(f"Unknown variable: {name}")
            variables[name] = value
        payload = render(load_json(args.path), variables)
        validate(args.kind, payload)
    except ContractError as error:
        message = str(error)
        if message.startswith("Unresolved placeholder:"):
            message += "; pass --var or --sample"
        print(message, file=sys.stderr)
        return 1
    print(f"Valid {args.kind}; offline validation only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
