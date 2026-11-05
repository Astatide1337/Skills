# Meaningful behavioral controls

Use when assessing a verifier or diagnosing a missing denied-operation check.
The linked [authorization example](authorization-example.py) is original,
fictional, in-memory teaching material. It is
not an application adapter, protected runner, or a claim about a real policy.
The author grants reuse of this instructional material within Skills and its
installed copies. It contains no external assets, personal records or secrets.

Its stated contract permits the matching owner in the matching tenant to edit
an active document. Other users, other tenants, anonymous clients and archived
documents are denied. A denial must preserve the entire document. The explicit
case table is the expectation, not whatever the candidate returns.

The exercise accepts both a centralized operation and a shared-policy design.
It rejects implementations that omit the tenant check or deny every operation.
This tests both acceptance of different valid designs and rejection of defects.
A permission error raised after an unauthorized mutation must also fail.

After reading the source, run the safe in-memory exercise with the interpreter
already available in the environment, resolving the path from this skill:

```sh
python skills/verify-work/references/authorization-example.py
```

A zero exit means the four *control decisions* matched their expected verdicts.
It does not mean all four implementations are correct. Inspect the printed
reasons: the version missing the tenant check must fail the different-tenant
case, and the version denying everything must fail the allowed-owner case.

For the real task, discover the application's permission policy and native
entry points. Replace these fictional rows with independently grounded allowed
and denied operations, including actual side effects. A hidden UI control
cannot establish server enforcement. A test that accepts two implementations
here cannot establish that a live evaluator accepts all valid architectures.

This case is shipped teaching material. Never call it held-out or use memorized
answers as evidence that guidance transfers. Use a new task or context to test that question, keep the requirement
discoverable, and record whether the case has already influenced development.
Keep application-specific policy with the application, not in this example.
