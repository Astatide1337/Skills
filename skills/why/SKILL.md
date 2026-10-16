---
name: why
description: When asked why code or architecture was designed this way.
---

# Why

Anchor the question to the relevant code, then search available history and
supplied decision evidence. Use read-only access. Code shows what happens; it
does not establish why someone chose it.

Treat a proposed reason as a hypothesis. Check contradictory sources and keep
important null results in the working notes. Distinguish documented reasons,
supported inference, plausible alternatives, and what the search did not
establish. Use confidence labels when useful rather than attaching a fixed tier
to every sentence.

Answer the actual question with adjacent source citations and the uncertainty
that affects the conclusion. State missing sources when their absence matters;
a separate source inventory or confidence summary is not required.

When recommending a change, identify current evidence needed to know whether
the historical constraint still applies: relevant configuration, migration
state, runtime behavior, or failure and cleanup evidence. Use the structure and
depth the recommendation needs.

Read `references/epistemics.md` when weighing evidence or resolving contradictions,
and `references/code-archaeology.md` for repository history investigations.
