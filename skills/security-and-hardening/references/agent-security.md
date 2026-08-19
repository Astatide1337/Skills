# Agent and LLM security

## Trust boundaries

- Treat user prompts, retrieved documents, web pages, files, tool output, model
  output, memory, and messages from other agents as untrusted data. Textual
  instructions do not create authorization.
- Keep permissions, tenant isolation, policy, and confirmation in deterministic
  application/tool boundaries rather than relying on the system prompt.
- Separate instructions from data structurally where possible, but do not claim
  delimiters or prompt wording eliminate prompt injection.

## Tools and actions

- Give the model the smallest tool set, data scope, credential, and action budget
  needed. Resolve tool arguments to allowlisted resources server-side.
- Require explicit authorization for high-impact or irreversible actions and
  re-check current state immediately before execution.
- Bind actions to the authenticated user and tenant. Prevent model-generated IDs,
  URLs, paths, SQL, or shell text from bypassing normal authorization and validation.
- Bound iterations, tokens, concurrency, time, spend, retrieval volume, and output
  size. Detect loops and repeated side effects.

## Retrieval and output

- Partition retrieval by tenant and authorization scope before similarity search;
  filter-at-display is too late. Track document provenance and deletion.
- Treat retrieved content as potentially poisoned. Do not let it request secrets,
  broaden tool access, or override application policy.
- Parse model output into a strict schema and allowlist actions and parameters.
  Never pass raw output to a shell, query engine, HTML sink, filesystem path, or
  privileged API.
- Minimize sensitive prompt context and provider retention. Test indirect prompt
  injection, cross-tenant retrieval, data exfiltration, excessive agency, and
  unbounded-consumption cases with isolated fixtures.
