# Artifact selection

Choose the first form that can encode the workflow completely and safely.

| Form | Choose when | Reject when |
|---|---|---|
| Existing platform capability | The repository already has a native mechanism with the needed guarantees | It requires hidden dashboard state or cannot be versioned or verified |
| Declarative configuration | The work is choosing known values or mapping environments, targets, or policies | Execution, recovery, or derived state is still required |
| Schema | The recurring judgment is whether structured input is valid | Validation depends on runtime state or cross-field behavior the schema cannot express |
| Validator | Existing artifacts need bounded semantic or integrity checks | It silently repairs state or performs unrelated writes |
| Idempotent script | A deterministic transformation or bounded sequence must execute | Inputs or targets cannot be resolved safely before mutation |
| Task runner or CI | Existing commands need repository-owned ordering, gates, evidence, and shared execution | Local invocation is sufficient or the platform would become the only source of truth |
| Service | The workflow truly needs continuous availability, concurrency control, durable shared state, or an API boundary | A command, scheduled job, or existing platform primitive is enough |

## Tie-breakers

Prefer fewer owners, less persistent state, fewer credentials, narrower permissions, local reproducibility, explicit inputs, and deletion over synchronization. Count the maintenance surface introduced, not only the commands removed.

Do not automate a rare, high-judgment procedure merely because it is tedious. Document it once and record what frequency, failure rate, or evidence would justify revisiting automation.
