# Workflow specification

Use this template before implementing a workflow with several steps, shared
state or recovery requirements. Omit fields that do not apply.

## Purpose

- Outcome:
- Repeated decision or failure being removed:
- Workflow class: repository-local, delivery, or agent operation
- Owner:
- Trigger for revision or retirement:

## Contract

- Trigger:
- Explicit inputs and allowed values:
- Preconditions:
- Invariants:
- Outputs or resulting state:
- Declared filesystem effects:
- Declared network or external effects:
- Secret source and handling:

## Execution

- Selected implementation form and why simpler forms are insufficient:
- Step ordering:
- Timeout and retry bounds:
- Idempotency mechanism:
- Concurrency behavior:
- Dry-run semantics, including what it still touches:

## Failure and recovery

- Fail-closed conditions:
- Partial-state detection:
- Recovery or rollback:
- Step requiring human input, and evidence needed for that decision:

## Proof

- Clean-checkout command:
- Normal-path fixture and assertion:
- Invalid-input fixture and assertion:
- Rerun assertion:
- Check for unintended writes or other effects:
- Superseded procedure removed or redirected:
