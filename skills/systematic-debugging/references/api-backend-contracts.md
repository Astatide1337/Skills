# API/backend debugging and contract evolution

## Trigger

Use this procedure when an HTTP or RPC caller receives an unexpected response,
an implementation conflicts with an API contract, or a contract change may
affect existing callers. Do not use it for a local function bug with no
transport or caller-contract question.

This procedure specializes `systematic-debugging`; keep its reproduce, inspect,
hypothesis, smallest-check, and original-failure verification sequence.

## Procedure

1. **Write down the observable contract.** Record the caller, method/operation,
   target, relevant headers or identity, request fields, response shape,
   status/error behavior, and version. Use redacted values for credentials and
   user data. Mark each expected fact with its source and scope: an owned
   schema, a supplied provider contract, a caller-level acceptance test, an
   implementation, or a test double. Do not promote a permissive mock or a
   matching implementation into normative evidence by itself.
2. **Trace the actual owner path.** Follow the request from caller through the
   transport serializer, authentication/authorization and parsing boundary,
   handler, domain owner, dependency or storage call, and response/error
   mapper. Omit layers that the code does not have. Name the first layer where
   observed behavior diverges from the chosen contract and identify callers
   that rely on that shape.
3. **Choose one discriminating observation.** Run the smallest local request
   or test that can fail on the mismatch. If external access is not explicitly
   in scope, use a runner-owned contract adapter or captured local request;
   state that this verifies only the supplied contract, not a live provider.
   Keep one valid request as a control and add a malformed, unauthorized, or
   incompatible request that should fail at the boundary.
4. **Change the owning layer.** Parse and validate external data at the
   boundary, keep domain behavior in its owner, and map internal failures to
   the established public response. For an evolution, list affected callers
   and old/new shapes; decide whether compatibility, versioning, a staged
   rollout, or a data migration is required from evidence. Do not add a version
   bump or migration merely because a schema changed.
5. **Verify the contract matrix.** Re-run the original request against the
   final code. Exercise allowed and rejected input, empty and varied results,
   and compatibility cases that the change can affect. Preserve distinct
   evidence for a transport contract, a local unit double, and the real
   service. A green unit double cannot substitute for a contract assertion.
6. **Bound the conclusion.** Report the exact caller and environment tested,
   the source that defined the expected behavior, the checks and observed
   responses, affected compatibility decisions, and unknown provider or
   deployment behavior. Do not claim live API compatibility from a local
   adapter.

## Executable example and negative control

From the repository root, run the existing contract-provenance case:

```bash
uv run --frozen python -m unittest \
  evals.tests.test_workflows.WorkflowContractTests.test_api_contract_provenance_keeps_the_valid_unit_mock_control -v
```

The test starts with a client that passes the visible permissive smoke mock but
fails the runner-owned contract check. The corrected client must pass that
contract check while the explicitly scoped local unit mock remains valid. A
candidate-edited smoke test or printed `PASS` is a negative control and must
not satisfy acceptance. This deterministic fixture checks the contract
distinction; it does not measure agent performance or establish a production
API fact.
