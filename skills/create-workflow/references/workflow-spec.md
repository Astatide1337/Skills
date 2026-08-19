# Workflow specification

Complete this compact contract for a non-trivial workflow. Omit fields that genuinely do not apply.

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

- Selected artifact and why simpler forms failed:
- Step ordering:
- Timeout and retry bounds:
- Idempotency mechanism:
- Concurrency behavior:
- Dry-run semantics, including what it still touches:

## Failure and recovery

- Fail-closed conditions:
- Partial-state detection:
- Recovery or rollback:
- Manual boundary and escalation evidence:

## Proof

- Clean-checkout command:
- Normal-path fixture and assertion:
- Invalid-input fixture and assertion:
- Rerun assertion:
- Side-effect observation:
- Superseded procedure removed or redirected:
