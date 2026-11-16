# Simplicity and reader load

Adapted from pstack's Laziness Protocol and Minimize Reader Load. Apply it with
the repository's code-review standards.

## Trigger

Use when an adapter, helper, dependency, state field, abstraction, or cleanup
is being considered, or when a reviewer cannot quickly explain where behavior
comes from.

## Before writing code

Load and apply the unmodified upstream [Ponytail core
skill](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md)
through the active harness's supported plugin or skill integration. At each new
coding task, refresh to the latest upstream through that integration, then load
the core skill from the location in the harness's skill metadata or manager
result. Without a native integration, fetch and read the linked upstream core
file directly. Keep that revision for the task; a plugin listing or mode flag
alone does not establish loading.

Keep setup and updates with the harness's native manager. Consult [upstream
installation instructions](https://github.com/DietrichGebert/ponytail/blob/main/INSTALL.md)
only when setup or recovery is needed; reuse a working installation. Honor user
overrides, hook trust, complete requested behavior and required checks. If
refresh or loading fails, stop dependent coding and report the failed stage and
supported recovery unless the user explicitly permits proceeding without it.

## Decision rule

Prefer the smallest design that removes a real problem. Count both the layers a
reader must trace and the mutable state they must remember. Keep an interface
only when it hides meaningful decisions or removes more complexity than it
introduces.

## Procedure

1. Identify what the proposed layer, field, or dependency removes for a caller
   or maintainer.
2. Delete dead code, pass-through wrappers, duplicate validators, and unused
   compatibility paths before adding structure.
3. Keep state local and derive values instead of synchronizing copies.
4. Prefer an explicit sequence over a framework when the sequence is the real
   domain. Prefer a domain boundary over a grab-bag utility module.
5. Read the changed path as a new maintainer. If the source of a value or its
   writers are unclear, flatten the path or name the invariant at the boundary.

## Evidence

Review the final diff for removed indirection and unchanged ownership. Explain
what each new component does and why that benefit warrants maintaining it. A
lower line count is not proof if it hides behavior or weakens a contract.

## Example

Reuse the existing database client and test runner for a pagination correction.
Do not introduce a generic pagination library whose only caller is the repaired
function.

## Limit

Do not flatten a boundary that isolates a genuine failure mode, security policy,
or independently evolving contract. Simplicity means fewer unnecessary
decisions, not fewer files at any cost.
