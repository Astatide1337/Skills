# Maintainability through a credible next change

Use for a consequential new ownership boundary or recurring maintainability
failure. Do not run for a typo, impose a universal architecture, or ship an extra
feature solely to demonstrate extensibility. Review-only remains read-only until
a disposable execution is authorized.

## Review the current design early

Trace the behavior's owner, callers, canonical types, authorization, validation
and state flow. Reuse the application's accepted feature patterns where they fit.
Ask which new dependency or abstraction serves a present requirement. A clearer
alternative can be valid even if it differs from the reference. Existing auth,
modal, share and state owners must not acquire unnoticed competitors.

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
A coherent option has one authoritative operation called by both entry points:

```python
def edit_document(actor, document, label):
    if (actor.user_id, actor.tenant_id) != (document.owner_id, document.tenant_id):
        raise PermissionError
    document.label = label
```

A valid alternative is a shared policy function invoked by separately owned
operations when those operations genuinely differ. A single local operation
with one consumer may need no abstraction at all. The lesson is coherent
ownership, not a service class, function count or universal file layout.

## The follow-up probe

Choose a plausible next requirement from actual planned work. For the example,
make archived documents read-only, but only when that is an authorized exercise.
Use a disposable copy of the identified candidate, with no unrelated credentials.
A fresh context receives ordinary project guidance and the follow-up, not the
original author's full explanation. Keep the original acceptance protected.

Observe whether the agent finds the right owner, changes every affected entry
point coherently and preserves the contracts. Inspect unexpected coupling,
manual synchronization and undocumented assumptions. Several changed files may
be appropriate. A small diff can still be wrong. No lines-of-code score decides.
Retain the probe result outside the deliverable and discard only owned scratch
work. Do not publish its extra feature without a separate request.

## Acceptance and limits

Require concrete findings about the current change, with evidence and a finite
resolution condition. Separate optional preferences. A successful probe supports
that follow-up scenario, not years of maintainability. Subsequent real changes
supply stronger evidence. Retire the probe when it is speculative, expensive or
unrepresentative rather than optimizing the codebase around it.

Source: original instructional example for Skills v2 (2026-10-13). No application
incident, expert acceptance or user-specific policy is asserted. Prefer actual
application-owned source examples when available.
