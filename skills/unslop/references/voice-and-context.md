# Voice and context

Natural writing is appropriate to its author and destination. It is not a bag
of quirks applied to every draft.

## Recover the available voice

Look for evidence already present in the source or request:

- stated opinions and emotional reactions;
- formality and relationship to the audience;
- characteristic sentence length, humor, directness, or restraint;
- first-person or collective perspective;
- domain vocabulary the audience expects.

Preserve those signals when they help the reader recognize the author. If the
source has no authorial evidence, choose a clear, restrained voice rather than
inventing a personality.

## Make voice-mode prose natural

- Let the author react to facts when the source supports the reaction.
- Vary sentence length according to emphasis and thought, not a fixed pattern.
- Preserve mixed reactions and real tradeoffs instead of resolving everything
  into a balanced conclusion.
- Use first person when the author owns an observation, decision, or
  experience. Do not use it to fabricate one.
- Prefer a specific image, action, or consequence over a generic feeling.
- Allow asymmetry when the subject warrants it. Natural writing does not need
  equal numbers of benefits, risks, and examples.

Do not manufacture typos, fragments, jokes, slang, controversy, or disorder to
look human. Deliberate clarity is not an AI tell.

## Protect factual modes

Incident reports, runbooks, research summaries, release notes, and technical
documentation should not acquire opinions or emotional color during cleanup.
They can still sound natural through direct syntax, concrete mechanisms,
appropriate cadence, and honest uncertainty.

Keep domain terms when they are exact. For example, "API surface" may be the
recognized set of public interfaces, "test harness" may name a real executable
system, and passive voice may correctly emphasize a result whose actor does not
matter. Fix vagueness, not vocabulary by category.

## Protect agent-facing modes

For prompts and instructions:

- prefer observable actions and stop conditions;
- keep literal paths, commands, schemas, and output contracts exact;
- preserve precedence, scope, authority, and safety boundaries;
- remove motivational language, anthropomorphic theater, and repeated framing;
- do not add stylistic variation that makes repeated instructions inconsistent.

Use `writing-for-agents` for general agent instructions and `skill-creator` for
skills. Their reliability rules override voice preferences.

## Mixed documents

Apply voice by section rather than averaging the whole document into one tone.
A personal introduction may use first person; the procedure that follows should
remain literal. Product copy may carry a point of view; its security or pricing
claims still require factual support.

