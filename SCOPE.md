# What belongs in this catalog

Models already know general engineering advice. A change earns a place here
only when it fixes something agents actually got wrong and the fix is shown
to help.

## A change is accepted when

1. **It answers an observed failure.** Link at least two occurrences of the
   same mistake class (sessions, commits, reviews), or one occurrence plus a
   reproduction. A good idea with no observed failure is not enough.
2. **It uses the strongest form that works.** Prefer a check, script or test
   an agent cannot skip over instruction text. See
   [learn from repeats](skills/self-reflect/references/learn-from-repeats.md).
3. **It belongs here, not in an application repository.** The mistake recurs
   across repositories or concerns how agents work, rather than one codebase.
4. **It is measured.** A before/after eval case, or a check proven to fail on
   the past mistake, shows the change helps and does not regress existing
   cases. See [measured improvement](skills/skill-creator/references/measured-improvement.md).
5. **It is the smallest change.** Deleting or tightening existing text counts
   as an improvement.

## Not accepted

- Rules distilled from one task's context.
- Personas, slogans, or general best practices with no observed failure.
- Changes that lower a verification bar to make an agent's work pass.
- Duplicate guidance already enforced by a check.

## Declined proposals

Record each declined proposal and its reason in
[docs/learning/rejected.md](docs/learning/rejected.md). Check it before
proposing. Re-propose only with new evidence.
