---
name: unslop
description: Rewrite prose to remove recognizable AI patterns while preserving meaning and producing a natural voice appropriate to the context. Use for padded, generic, repetitive, theatrical, sterile, overly polished, or formulaic drafts, including documentation, explanations, plans, reports, review comments, posts, essays, and product copy. Do not use to alter quoted text, impose personality on factual or agent-facing instructions, or rewrite already-natural prose merely to enforce a house style.
---

# Unslop

Remove generated-looking language without removing the writer.

## 1. Lock what must survive

Inventory the source's atomic facts, decisions, instructions, citations,
qualifications, uncertainties, and intentional opinions. Also identify the
audience, destination, and requested tone. Do not mistake unsupported praise,
importance claims, or emotional framing for facts unless the request makes
them substantive.

Preserve exact technical terms, quoted material, links, numbers, commitments,
and uncertainty. Flag ambiguity rather than silently resolving it.

## 2. Choose the mode

- **Factual:** reports, documentation, plans, incidents, and technical
  explanations. Remove rhetoric and name mechanisms. Do not add opinions,
  personality, confidence, or claims.
- **Voice:** essays, posts, product copy, and conversational explanations.
  Preserve or strengthen the source's real perspective, rhythm, and emotional
  complexity without inventing experiences or a persona.
- **Agent-facing:** prompts, runbooks, `AGENTS.md`, and `SKILL.md`. Precision,
  scope, evidence, and executable wording outrank human texture. Follow
  `writing-for-agents` or `skill-creator` when applicable; use this skill only
  to remove padding, vague directives, repetition, and promotional framing.

If the destination mixes modes, classify each section separately. Read
[voice and context](references/voice-and-context.md) before a voice-mode or
mixed-mode rewrite.

## 3. Diagnose before rewriting

Read the [AI-pattern catalog](references/ai-patterns.md). Treat its entries as
signals, not automatic violations. A term or construction may be correct when
it is concrete, conventional in the domain, present in a quotation, or part of
the writer's established voice.

Mark patterns that materially affect this draft. Do not mechanically replace a
word while leaving the same vague sentence intact.

## 4. Reconstruct the draft

Rebuild from the preserved inventory when sentence-by-sentence editing would
retain the original framing. Otherwise make the smallest edits that remove the
identified tells.

- Prefer concrete nouns and verbs. Name the actor, mechanism, or measured
  result when known.
- Keep one term per concept and use the natural number of examples or clauses.
- Split sentences that require backtracking, but do not turn useful prose into
  clipped fragments.
- Vary rhythm only when the mode permits it. Natural writing is not random
  sentence-length alternation.
- Remove generic setup, summaries that add nothing, canned transitions,
  sycophancy, and unsupported self-assessment.
- Keep purposeful structure. Do not introduce mess, first person, jokes, or
  opinions merely to simulate humanity.

## 5. Audit the result

Check the revision in this order:

1. **Fidelity:** every required fact, decision, instruction, citation,
   qualification, and uncertainty survived.
2. **No invention:** no new fact, source, experience, opinion, or confidence
   appeared without support.
3. **Context:** factual sections remain factual, voice sections sound like the
   intended author, and agent instructions remain testable.
4. **AI tells:** ask what still makes the text feel generated, then fix the
   remaining substantive patterns rather than chasing isolated words.
5. **Naturalness:** read it as a whole. Restore useful transitions or cadence
   if removal made it sterile or abrupt.

Return the revision in the exact requested destination and format. Add a note
only when ambiguity, conflicting constraints, or a meaning-changing cut needs
the user's decision.
