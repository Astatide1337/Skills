# Dataflow and failure paths

Use when designing a consequential boundary, asynchronous flow, migration or
recovery path. A local mechanical change needs no architecture questionnaire.

1. Trace one realistic operation from caller through validation, authoritative
   state, external effects and response. Identify ownership at each crossing.
2. Ask what happens after a timeout, duplicate request, partial write, stale
   read, cancellation or unavailable dependency. Inspect only cases the flow
   can actually enter.
3. Identify the commit point, retry owner and idempotency key where relevant.
   Define what remains true if one component fails; avoid two owners deciding
   the same recovery action.
4. Check observability: which result or event distinguishes success, rejection,
   partial completion and retry? Do not log sensitive payloads for convenience.
5. Compare a competing design only when it changes a real tradeoff. Prefer the
   design with clear invariants and fewer coordinated changes, not more layers.
6. Derive acceptance scenarios from success and material failure paths. Keep
   them in existing tests or project decisions instead of a second spec system.

Method provenance: original synthesis informed by
[gstack engineering review](https://github.com/garrytan/gstack/blob/main/plan-eng-review/SKILL.md)
and the repository's ownership principles. No upstream workflow or text is
vendored; no additional approval, merge or tool authority is implied.
