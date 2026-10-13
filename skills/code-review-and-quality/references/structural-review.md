# Thermonuclear structural lens

Use for significant ownership/interface/state changes or an explicit deep
review. Keep correctness as the primary review; structural taste is not a defect.

- Locate the decision owners and trace their callers. Does duplicated state or
  an alternate write path allow conflicting truth?
- Follow branching and error propagation. Can a demonstrated invariant remove
  cases, or is an extra abstraction merely moving the same decisions?
- Identify wrappers, translation layers and configuration with no real consumer
  or hidden complexity. Check dynamic entry points before calling code dead.
- Examine lifecycle, cancellation, retries and resource cleanup across boundaries.
  Would an ordinary addition require unrelated modules to coordinate?
- Propose the simplest equally correct alternative. Explain preserved behavior,
  affected ownership and the check that would detect regression.

Combine findings with correctness, framework and
[behavior-preserving simplification](behavior-preserving-simplification.md).
Deduplicate by underlying defect; label optional improvements separately. Do
not rewrite a working system because the review's name implies aggression.
Repeat only after material edits or unresolved findings.

Method provenance: original questions informed by Cursor's
[thermonuclear code-quality review](https://github.com/cursor/plugins/blob/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md).
This adapts the structural perspective without copying the upstream skill or
adopting a second coordinator.
