# Public engineering case studies

Load this reference only when a decision matches a case. These are short
paraphrases of primary sources. “Source reports” is deliberately separated
from “local adaptation”; neither the companies' architecture nor their scale
is a default for a small application.

## Shopify: modular monolith

**Source:** [Under Deconstruction: The State of Shopify's Monolith](https://shopify.engineering/shopify-monolith), Shopify Engineering, published 2020.

- **Problem:** A very large Rails monolith needed clearer ownership and more
  local reasoning without stopping feature work.
- **Constraints:** Hundreds of developers, legacy code, and a dependency graph
  with cycles made a single central redesign unrealistic.
- **Engineering decision:** Shopify organized code into owned components,
  simplified dependency direction, adopted Rails Engines and static Packwerk
  checks, and used Sorbet for boundary contracts. The source says the details
  changed substantially after the original effort. In particular, the team
  moved away from many hard interface-consistency rules and an earlier dynamic
  call-graph tool when those added friction or noise.
- **Trade-off:** Ownership and change locality improved while the monolith
  remained. Boundaries and tooling still cost work, and Shopify split out only
  cases with a strong reason, such as high-throughput read-only rendering or
  sensitive card vaulting.
- **Evidence:** The article reports explicit component ownership, Packwerk on a
  subset of components, and continued progress toward an acyclic graph.
- **When it does not apply:** A small service with one clear owner may gain
  nothing from component machinery or a service split.
- **Local adaptation:** Before adding a service, inspect the current caller and
  owner. After the change, keep a local module boundary and one verifiable
  contract. This uses `establish state and ownership first` and the
  `implement/refactor` or `design/plan` playbook; it does not import Shopify's
  tools.

## Stripe: idempotent API effects

**Source:** [Designing robust and predictable APIs with idempotency](https://stripe.com/blog/idempotency), Stripe Engineering.

- **Problem:** A network failure can leave a client unsure whether a mutating
  request completed.
- **Constraints:** Retrying a non-idempotent operation can duplicate an effect,
  while not retrying can leave state incomplete.
- **Engineering decision:** Stripe describes idempotency keys on mutating
  endpoints. The server associates a key with the request and can return the
  original result on a safe retry. The article also recommends bounded
  exponential backoff with jitter for repeated failures.
- **Trade-off:** The server must retain and validate request identity and
  payload, and clients still need a retry policy. A key with a different
  payload must not silently become a new operation.
- **Evidence:** The source explains connection, mid-operation, and response
  failures and the one-effect retry behavior for the same key.
- **When it does not apply:** Read-only requests or operations whose natural
  semantics already converge do not need a new key store, and a key cannot
  make an unsafe side effect safe if the server does not own the state.
- **Local adaptation:** For an external create, persist one operation identity,
  tolerate an ambiguous response by replaying the same payload, and verify the
  same object. This uses `make claims match evidence`, `issues`, and
  `migrate-operate`; it is not a reason to build a general retry service.

## SQLite: test failure and recovery

**Source:** [How SQLite Is Tested](https://www.sqlite.org/testing.html), SQLite.

- **Problem:** Correct results on healthy, well-formed inputs do not establish
  robustness when memory, I/O, files, or processes fail.
- **Constraints:** Failure paths are numerous and can corrupt durable state if
  they are only reasoned about.
- **Engineering decision:** SQLite describes independent harnesses, regression
  tests, malformed-input tests, fuzzing, and deliberate out-of-memory, I/O,
  crash, and power-loss checks. A reported bug is not considered fixed until a
  regression case is added.
- **Trade-off:** This testing effort is much larger than the production code
  and requires specialized tooling. It buys confidence about failure modes,
  not a guarantee for every environment.
- **Evidence:** The source lists the harnesses and describes checking database
  integrity after injected I/O failures.
- **When it does not apply:** A small pure function does not need SQLite's
  millions of cases or private harnesses. It still needs a regression and the
  relevant negative path.
- **Local adaptation:** Preserve the original failing test, add one failure or
  recovery control that can fail for the bug, then run the real project path.
  This uses `investigate causes and test behavior` and `implement/bug`.

## GitHub: October 2018 recovery

**Source:** [October 21 post-incident analysis](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/), GitHub, published October 30, 2018.

- **Problem:** A short network partition triggered stale and inconsistent views
  across database replicas and a long service degradation.
- **Constraints:** Resuming writes or queued work too early could compound data
  inconsistency. Availability and integrity were in tension.
- **Engineering decision:** GitHub paused metadata-writing jobs, restored and
  synchronized databases, processed backlogs, and kept the status degraded
  until queued work and system behavior had settled. The source explicitly
  describes choosing data integrity over a shorter outage.
- **Trade-off:** Users experienced degraded features for longer, and recovery
  required careful observation of replica lag, backlog, and topology.
- **Evidence:** The report describes the timeline, replica delay, backlog
  processing, and the later green status only after integrity and operation were
  confirmed.
- **When it does not apply:** A local reversible edit does not require a
  multi-region failover plan. Do not borrow incident ceremony for a unit test.
- **Local adaptation:** During an operational task, distinguish mitigation from
  diagnosis, inspect actual state before declaring recovery, and verify the
  requested runtime behavior after convergence. This uses `migrate-operate` and
  `verify-work`.

## GOV.UK: actionable form errors

**Source:** [GOV.UK Design System error summary](https://design-system.service.gov.uk/components/error-summary/).

- **Problem:** A validation error that is only styled or placed beside a field
  can be missed, especially by keyboard and screen-reader users.
- **Constraints:** The user must find the problem, understand the correction,
  and reach the affected input without hunting through the page.
- **Engineering decision:** GOV.UK requires an error summary, a clear heading,
  links to each invalid answer, matching wording beside the input, and keyboard
  focus moved to the summary.
- **Trade-off:** The page needs an explicit error state and stable field links;
  generic toast notifications are simpler but less actionable.
- **Evidence:** The design-system guidance states these focus, heading, link,
  and wording requirements and shows the corresponding markup.
- **When it does not apply:** Do not add a summary to a non-interactive status
  message or copy the visual component without the underlying validation and
  focus behavior.
- **Local adaptation:** For a real form, test submit, error focus, keyboard
  navigation, and correction. This uses `web-interface`, `verify-work`, and the
  relevant `implement/feature` playbook; a screenshot alone is not proof.

These examples teach contrasts, not templates. Record the source-reported fact,
the local decision it changes, and the boundary where the simpler alternative
is better.
