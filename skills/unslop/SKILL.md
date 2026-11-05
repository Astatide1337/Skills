---
name: unslop
description: "Use when writing or revising prose, including docs, PR descriptions and reports. Use code-review-and-quality for code cleanup."
---

# Unslop

Write for the intended reader and purpose. Preserve the writer's meaning and
voice. Base new drafts on supplied facts. Use temporary files for outlines or
alternative drafts when useful, and put the finished text in the requested
destination.

## Writing standards

Use [plain-language and STE guidance](references/plain-language-and-ste.md)
when the document needs a writing standard. Its STE guidance is useful for
technical procedures and text that must translate consistently. Apply a formal
standard when required, but claim compliance only after the required review.
Preserve the intended voice.

## 1. Lock what must survive

Identify the facts, decisions, instructions, citations, qualifications,
uncertainties and intentional opinions that must survive the edit. Establish
the audience, destination and requested tone. Unsupported praise and claims of
importance are not facts; keep them only when they are part of the requested
content.

Preserve exact technical terms, quoted material, links, numbers, commitments,
and uncertainty. Flag ambiguity rather than silently resolving it.

## 2. Choose the mode

- **Factual:** reports, documentation, plans, incidents, and technical
  explanations. Remove manufactured drama and name mechanisms. Do not add opinions,
  personality, confidence, or claims.
- **Voice:** essays, posts, product copy, and conversational explanations.
  Preserve or strengthen the source's real perspective, rhythm, and emotional
  complexity without inventing experiences or a persona.
- **Agent-facing:** prompts, runbooks, `AGENTS.md` and `SKILL.md`. Keep actions,
  scope, permissions and evidence precise. Follow `writing-for-agents` or
  `skill-creator` as applicable. Use this skill to remove padding, vague
  instructions, repetition and promotional framing.

If the destination mixes modes, classify each section separately. Read
[voice and context](references/voice-and-context.md) before a voice-mode or
mixed-mode rewrite.

## 3. Diagnose before rewriting

Check the structure before polishing sentences. Does the opening answer the
reader's question? Does each section supply what the next one needs? Move
misplaced background, reduce overemphasized minor points and remove conclusions
that invent a lesson or resolution. Read
[composition and progression](references/voice-and-context.md#composition-and-progression)
when repairing structure. Preserve required output formats.

Read the [AI-pattern catalog](references/ai-patterns.md). Treat its entries as
signals, not automatic violations. A term or construction may be correct when
it is concrete, conventional in the domain, present in a quotation, or part of
the writer's established voice.

Mark patterns that materially affect this draft. Do not mechanically replace a
word while leaving the same vague sentence intact.

Check overexplanation at the idea level as well as the sentence level. Mark
repeated conclusions, background the audience already knows, exhaustive
edge-case lists unrelated to their decision, and explanations of an obvious
example. Shortening each sentence while keeping all that material is not enough.

## 4. Reconstruct the draft

Rewrite from the facts and requirements you preserved if editing individual
sentences would leave the structural problem intact. Otherwise fix the
specific passages that need work.

Choose the opening and sequence for this particular purpose. An explanation
may follow a concrete case through its cause; a story may let an event change
what the reader expects. These are possibilities, not required outlines. Allocate
detail to the reader's needs; the central point may take only a sentence. Connect
paragraphs through an actual dependency, consequence, or question carried
forward; a transition word cannot supply a missing connection. Do not force
every piece into setup, problem, solution, benefits, and a reassuring conclusion.

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

Cut repetition and background that do not help this audience. Preserve the
requested depth, material exceptions, and uncertainty. Include a recap or next
step when it helps the reader; end once the request is satisfied.

For a voice rewrite, use relevant author examples already supplied to identify
tone and phrasing. Diagnose a specific passage, edit it, then compare its meaning
with the original. Leave effective passages alone.

## 5. Audit the result

Check the revision in this order:

1. **Fidelity:** every required fact, decision, instruction, citation,
   qualification, and uncertainty survived.
2. **No invention:** no new fact, source, experience, opinion, or confidence
   appeared without support.
3. **Context:** factual sections remain factual, voice sections sound like the
   intended author, and agent instructions remain testable.
   Check that the opening, order, emphasis, and ending serve the intended purpose.
4. **AI tells:** remove remaining vague claims, padding, repeated ideas and
   formulaic phrasing. Judge the sentence in context, not by isolated words.
5. **Naturalness:** read it as a whole. Restore useful transitions or cadence
   if removal made it sterile or abrupt.
6. **Proportion:** every remaining paragraph earns its space. Do not compress
   away a required fact to meet an arbitrary length or detector score.

## Handoff voice

When the text is a progress or completion handoff, lead with the result and
evidence. Mention an unperformed action only when it changes the user's next
decision; state that limitation once, then offer the next useful step. Do not
turn authorization boundaries into repeated "I have not ..." disclaimers.

Return the revision in the exact requested destination and format. Add a note
only when ambiguity, conflicting constraints, or a meaning-changing cut needs
the user's decision.
