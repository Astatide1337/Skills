"""Original instructional controls, not an application verifier or security sandbox.

All records are fictional and in memory. Expected results are explicit policy
examples, not inferred from a candidate. Two different valid implementations
must pass; deny-everything and happy-path-only implementations must fail.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Actor:
    tenant: str
    user: str


@dataclass
class Document:
    tenant: str = "team-a"
    owner: str = "owner"
    label: str = "before"
    archived: bool = False


Edit = Callable[[Actor | None, Document, str], None]


def centralized_edit(actor: Actor | None, document: Document, label: str) -> None:
    if actor is None or (actor.tenant, actor.user) != (document.tenant, document.owner):
        raise PermissionError("not the owner in this tenant")
    if document.archived:
        raise PermissionError("archived document")
    document.label = label


def policy_allows(actor: Actor | None, document: Document) -> bool:
    return (actor is not None and actor.tenant == document.tenant
            and actor.user == document.owner and not document.archived)


def policy_based_edit(actor: Actor | None, document: Document, label: str) -> None:
    if not policy_allows(actor, document):
        raise PermissionError("editing denied")
    document.label = label


def happy_path_only(actor: Actor | None, document: Document, label: str) -> None:
    # Intentionally defective: same user identifier in another tenant gets in.
    if actor is None or actor.user != document.owner or document.archived:
        raise PermissionError("editing denied")
    document.label = label


def deny_everything(actor: Actor | None, document: Document, label: str) -> None:
    raise PermissionError("editing denied")


# Explicit independent expectations for this illustrative policy.
# These rows are development/teaching material, never a claimed held-out set.
CASES = (
    ("owner", Actor("team-a", "owner"), False, True),
    ("different-user", Actor("team-a", "other"), False, False),
    ("different-tenant", Actor("team-b", "owner"), False, False),
    ("anonymous", None, False, False),
    ("archived-owner", Actor("team-a", "owner"), True, False),
)


def violations(candidate: Edit) -> list[str]:
    failures = []
    for name, actor, archived, expected_allowed in CASES:
        document = Document(archived=archived)
        original = vars(document).copy()
        try:
            candidate(actor, document, "after")
            allowed = True
        except PermissionError:
            allowed = False
        except Exception as exc:
            failures.append(f"{name}: unexpected {type(exc).__name__}")
            continue
        expected_state = {**original, "label": "after"} if expected_allowed else original
        if allowed != expected_allowed or vars(document) != expected_state:
            failures.append(name)
    return failures


def main() -> int:
    controls = ((centralized_edit, True), (policy_based_edit, True),
                (happy_path_only, False), (deny_everything, False))
    passed = True
    for candidate, expected in controls:
        failed_cases = violations(candidate)
        accepted = not failed_cases
        passed = passed and accepted == expected
        print(f"{candidate.__name__}: {'accepted' if accepted else 'rejected'}"
              f"; violated cases={failed_cases}")
    print("Instructional control results only. No product, agent or isolation claim.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
