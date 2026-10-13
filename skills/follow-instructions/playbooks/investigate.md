# Investigate / read

## When

Use for a read-only question about a repository or supplied evidence. A sufficient pasted snippet can be answered directly.

## Inputs to establish

- Exact question, source/revision, expected versus observed behavior, and read/network boundaries.
- Whether another artifact such as an issue is explicitly requested.

## Steps and decision points

1. Locate the actual owner, callers, configuration, and direct evidence before trusting a summary.
2. Separate observations from hypotheses. When causation is uncertain, choose an observation that distinguishes plausible causes; do not manufacture alternatives for a demonstrated mechanism.
3. Run the smallest authorized read-only check and update the explanation when evidence contradicts it.
4. Answer from source, logs, or traces. Use [debugging](../../systematic-debugging/SKILL.md), [how](../../how/SKILL.md), [why](../../why/SKILL.md), or [research](../../internet-reach/SKILL.md) only for their respective jobs.
5. If implementation is also requested, continue through [implement](implement.md); investigation alone grants no write authority.

## Failure and recovery

Try supported alternative sources and recoverable setup. Missing evidence is a gap, not proof that no cause or caller exists. Stop repeating retrieval without new information.

## Completion evidence

Give the direct answer, source locations, causal confidence, and relevant untested states. Diagnosis is not a fix.

## Example

Inspect a wrong-tenant lookup and explain the observed scope gap without changing code.

## Near-miss

A two-sentence pasted-code explanation does not require repository crawling.
