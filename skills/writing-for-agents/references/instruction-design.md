# Instruction design

## Point to context precisely

An instruction should tell the agent when information becomes relevant and
where to find it. A bare filename is weaker than a contextual pointer such as
"Before changing the schema, read `references/migrations.md`." The leading
words establish the trigger; the path supplies the detail.

Manage two costs:

- **Context load:** material consumes attention even when irrelevant.
- **Cognitive load:** scattered or ambiguous material makes the agent assemble
  the procedure itself.

Keep an essential ordered step inline. Keep a compact rule beside the step that
uses it. Disclose detailed variants through a directly linked reference. Split
by invocation or sequence, not merely by topic. Avoid chains of references.

When another file is declared authoritative, point to it and describe how to
apply it without restating its values. Repeating even a short checklist creates
two sources that can drift.

Co-locate instructions that must be applied together. Do not duplicate them.
Name one authoritative source when the repository, schema, configuration, or
runtime already contains the fact.

## Make completion difficult to fake

Define the observable end state, the evidence required, and what must happen
when a check fails. Avoid criteria such as "looks good," "properly handled," or
"production ready." Put the verification next to the action it verifies.

Guard against two failure modes:

- **Premature completion:** the agent stops after producing an artifact but
  before proving the requested behavior.
- **Post-completion drift:** the agent continues into publishing, deployment,
  cleanup, or adjacent improvements that were never authorized.

State explicit stop conditions and the handoff after successful verification.

## Write executable steps

Start steps with the action or condition: "Run," "Inspect," "If the test
fails," or "Before editing." Prefer positive instructions that name the desired
behavior. Use prohibitions for meaningful boundaries, and pair them with the
allowed alternative when ambiguity remains.

Explain why a non-obvious constraint exists. This helps the agent generalize
when the exact example changes. Examples should resolve a real ambiguity, not
decorate the rule.

## Prune instruction sediment

For every rule, ask:

1. What observable behavior changes if this sentence is removed?
2. Is the same rule authoritative elsewhere?
3. Is it still relevant to the current tools and workflow?
4. Can repository state or validation replace prose?

If removal changes nothing, delete it. If the environment already proves the
fact, point to that source or add a deterministic check. Rewrite accumulated
exceptions into the underlying decision rule instead of preserving the history
of every correction.
