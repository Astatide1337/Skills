# Choose verification layers

Start with a claim someone could disprove. Use the cheapest existing check that can disprove it. Add another layer when it observes a different failure mode. For each material claim retain the candidate revision, command or interaction, inputs, observed result and remaining blind spot.

| Question | Methods to consider | Evidence |
| --- | --- | --- |
| Can a caller express an invalid operation or supply invalid data? | Types, compiler, static analysis, lint, schema, configuration and contract tests | One invalid call or payload rejected at its owner and a supported alternative accepted. Exercise unchecked or legacy inputs at the boundary when they can bypass the type. |
| Does the built feature work? | Unit and component tests isolate a decision. Functional, integration, acceptance, smoke and regression tests exercise paths through it. | Launch the built candidate locally with isolated state and intended dependencies. Drive the real API or screen and observe the response, persisted value after reload or visible outcome. Identify any missing dependency and the unverified claim. |
| What happens with other inputs or action orders? | Fuzz tests, property-based tests and dynamic exploration | A reproducible input or action trace and an independent property that distinguishes success from failure. See the UI example below. |
| Which guarantees depend on a protocol or algorithm? | Formal verification through model checking or theorem proving | State the property, assumptions and scope, then connect the formal result to the actual implementation. |
| Can the checks detect this defect? | Coverage locates unexercised code. Mutation tests introduce a targeted fault. | Show which check fails on the fault and passes on a valid alternative. |
| How does the experience change under realistic conditions? | Usability and UI/UX tests, benchmarks, performance, load and soak tests, profiling | Observe a representative task or workload against a baseline. Capture its user outcome, latency or resource behavior over the relevant duration. |
| What does operation reveal? | Tap comparison using teeing or shadowing, traffic shaping, feature flags, canarying, A/B tests, real-user monitoring, exception tracking, logs/events, tracing, monitoring, auditing and on-call experience | Specify the signal, comparison and decision. Use authorized observations. A canary needs a control and evaluation window. Shadow traffic can trigger writes; verify isolation before replay. |
| Does a trust boundary or recovery contract hold? | Threat modeling, scoped penetration testing and controlled fault or chaos tests | Establish an authorized environment, the boundary or injected fault, and the observable denial or recovery. |

## Examples beyond the UI

- **Inputs and sequences.** For a codec, generate valid records and check
  that decoding the encoded bytes yields the original record. Fuzz malformed
  and truncated byte streams separately and check the documented error result.
  Keep a minimized failing input. Use a language-native fuzzer such as
  [Go fuzzing](https://go.dev/doc/security/fuzz/), or use
  [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html)
  for operations whose validity depends on earlier actions.
- **Compatibility and fault recovery.** For a changed message format, run a
  contract test with an older producer and the new reader. If delivery can
  repeat after a timeout, inject that fault in an isolated integration test
  and observe the number of stored records after retry. Coverage of the
  handler alone cannot distinguish one write from two.
- **Capacity over time.** Use a load test to find the concurrency at which
  latency crosses the agreed budget. For suspected resource growth, hold a
  representative workload steady and compare resource use over time in a
  [soak test](https://grafana.com/docs/k6/latest/testing-guides/test-types/soak-testing/).
  Record workload, duration and measurements for the build tested.

## Stateful UI

Choose actions the user can actually take, vary their order and define an invariant in user terms. For a draft editor, enter text, navigate between views and allow an older save response to arrive. The editor must preserve the newer text until it is explicitly discarded. Check the rendered text or persisted draft against the input; reading the component's own “saved” flag could miss data loss. Use the project's UI driver or [Bombadil](https://antithesishq.github.io/bombadil/browser/1-introduction.html) to run generated sequences on the local app. Exercise generated actions on the running UI itself when claiming UI property coverage. Report hand-picked browser replays and generated model transitions separately. Keep the initial state and seed or action trace. Minimize a failing sequence, replay it against the repaired build and retain the sequence as a regression.

## Protocols and algorithms

For competing writers, retries or order-dependent transitions, [TLC](https://lamport.azurewebsites.net/tla/tools.html) can explore a finite TLA+ model. Specify initial states, actions, invariants and bounds, including any fairness assumptions for liveness. Count states as reachable only after traversing legal transitions from the initial states. Label a Cartesian enumeration as assignments checked, even when it includes every reachable state. Exercise a known faulty transition to obtain a counterexample and check the corrected model. Map the trace back to actual API calls, messages or storage operations and replay the scenario on the implementation.

For a precise algorithmic guarantee, a [Lean proof](https://lean-lang.org/theorem_proving_in_lean4/) can establish a theorem under its stated assumptions. Check the theorem, record its preconditions and show how the shipped algorithm corresponds to the proved definition. Validate the adapter, numeric representation or other integration boundary with runtime cases where applicable. Report model or proof results separately from the implementation evidence.
