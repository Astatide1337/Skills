# Maintainability through a credible next change

Use when a new module boundary could affect later changes or when maintenance
problems keep recurring. Do not run for a typo, impose a universal architecture, or ship an extra
feature solely to demonstrate extensibility. Review-only remains read-only until
a disposable execution is authorized.

## Review the current design early

Trace the behavior's owner, callers, canonical types, authorization, validation
and state flow. Reuse the application's accepted feature patterns where they fit.
Ask which new dependency or abstraction serves a present requirement. A clearer
alternative can be valid even if it differs from the reference. Check that new code does
not duplicate existing authentication, modal, sharing
or state-management owners.

Types, schemas and approved import checks can enforce known boundaries. They do
not establish that the chosen boundary is useful. Review the consequential design
before broad implementation. Record a concrete coupling or duplication problem,
not merely that the folder structure looks unfamiliar.

## Original instructional comparison

Situation: two entry points edit a document. Both must enforce the same owner
and tenant rule. These small snippets illustrate ownership, not production code.

Rejected pattern:

```python
def edit_from_form(actor, document, label):
    if actor.user_id != document.owner_id:
        raise PermissionError
    document.label = label


def edit_from_api(actor, document, label):
    if actor.tenant_id != document.tenant_id or actor.user_id != document.owner_id:
        raise PermissionError
    document.label = label
```

The rules disagree. Hiding a form control does not repair its server-side path.
One solution puts the rule in an operation called by both entry points:

```python
def edit_document(actor, document, label):
    if (actor.user_id, actor.tenant_id) != (document.owner_id, document.tenant_id):
        raise PermissionError
    document.label = label
```

A valid alternative is a shared policy function invoked by separately owned
operations when those operations genuinely differ. A single local operation
with one consumer may need no abstraction at all. Keep the rule consistent across
callers. The example does not require a
service class, a particular function count or a standard file layout.

## The follow-up probe

Choose a plausible next requirement from actual planned work. For the example,
make archived documents read-only, but only when that is an authorized exercise.
Use a disposable copy of the identified candidate, with no unrelated credentials.
A fresh context receives ordinary project guidance and the follow-up, not the
original author's full explanation. Keep the original acceptance protected.

Observe whether the agent finds the right owner, changes every affected entry
point coherently and preserves the contracts. Inspect unexpected coupling,
manual synchronization and undocumented assumptions. Judge whether the change is correct
and easy to follow, not how many files or
lines it changes.
Retain the probe result outside the deliverable and discard only owned scratch
work. Do not publish its extra feature without a separate request.

## Acceptance and limits

For each finding, state the defect, evidence and what would resolve it. Separate
optional preferences. A successful probe supports
that follow-up scenario, not years of maintainability. Subsequent real changes
supply stronger evidence. Retire the probe when it is speculative, expensive or
unrepresentative rather than optimizing the codebase around it.

Source: original instructional example. No application
incident, expert acceptance or user-specific policy is asserted. Prefer actual
application-owned source examples when available.
