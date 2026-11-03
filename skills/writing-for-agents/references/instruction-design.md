# Instruction design

Use this reference to decide what an instruction needs to say, where to put
supporting detail and what to remove.

## Point to context precisely

Tell the agent when to read a reference and where to find it: “Before changing
the schema, read `references/migrations.md`.” A filename alone leaves the
reader to infer when it matters.

Keep ordered steps and the rules they depend on together. Link directly to
variants needed only for specific requests. Avoid making the agent follow a
chain of references to reconstruct one procedure.

State durable decisions in the instructions. Resolve changing model choices,
tool options, versions and environment facts from their authoritative owner at
use time. Keep exact commands with the adapter or runbook that tests them;
do not present an observed example as a permanent default.

When another file owns a rule, link to it and explain when to apply it.
Do not repeat its checklist or values; copies can drift. Extra context costs
attention, while missing or scattered context forces the reader to guess.

## Make completion difficult to fake

State the required result, the evidence that establishes it and what to do
when a check fails. Put the check beside the action it verifies. Replace
“looks good,” “properly handled” and “production ready” with observable results.

Prevent both premature completion and unauthorized follow-on work. Producing
an artifact is not enough if the task requires proving its behavior. Passing
checks does not authorize publication, deployment or unrelated cleanup.

For delivery, link to the completion requirements in
[`pull-requests`](../../pull-requests/SKILL.md). Do not define another delivery
procedure in each playbook. A checkpoint records pending work; it does not run
that work or cause a runtime to resume.

## Write executable steps

Start with the action or its condition: “Run,” “Inspect,” “If the test fails”
or “Before editing.” Prefer instructions that name the desired behavior.
Use prohibitions for real boundaries and explain the allowed alternative
when a reader might otherwise be stuck.

Explain a non-obvious constraint so the agent can apply it to a new case.
Use examples to resolve ambiguity. Keep requirements, defaults and examples
distinct: a preferred method need not be mandatory when another method meets
the same requirement.

Name actors and objects. “Inspect the failing run's output” is clearer than
“inspect it.” Keep the action, deciding observation and failure response
together. Fetching a page shell does not inspect an image; specify the
observation the task actually needs.

Give the instructions to a fresh reader. Check whether they take the intended
action, recover from a relevant failure and accept a valid alternative without
extra explanation. If a tool cannot supply a required observation, repair it
or report the limit. Stronger adjectives and phrase lint cannot replace that
behavioral check.

Anthropic's [context-engineering guidance](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
supports supplying enough context for the decision and loading detail when
needed. It does not establish that this catalog improves agent performance.

## Prune instruction sediment

For each rule, ask:

1. What action would change if this sentence were removed?
2. Does another authoritative source already state it?
3. Does it still apply to the current tools and workflow?
4. Can repository state or a check replace it?

Delete sentences that change no action. Link to facts already established
elsewhere. Replace accumulated exceptions with the decision rule they share,
while preserving exceptions that still change the required behavior.
