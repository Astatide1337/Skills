# Sourced AI-code failures

Use when plausible generated code needs a concrete integration or code-health
counterexample. Sources explicitly identify the artifacts as AI-generated.
Authorship is not inferred from style. These historical examples do not establish
failure rates for today's models or for this preview.

## A helper exists but the interaction never reaches it

[Anthropic's experiment report][anthropic] describes a rectangle-fill operation
whose helper existed but was not correctly connected to the mouse-up event.
Only the endpoints changed.

**Review:** Exercise an actual drag and check interior and surrounding cells.
A helper's presence and isolated tests do not prove event wiring. Inspect the
existing owner before adding another implementation. This is the source author's
reported result, not our execution of that original app.

## A route exists but ordered matching shadows it

The [same report][anthropic] describes a reorder endpoint shadowed by an integer
parameter route. [FastAPI's route-order guidance][fastapi] explains the mechanism.

```text
# Reconstruction of the reported order, not copied application code
PUT /frames/{frame_id}
PUT /frames/reorder
```

**Review:** Call through the actual router and check both operations. Moving the
literal route earlier is one correction. A different unambiguous URL can be
valid when interface changes are authorized. Weakening integer validation merely
to avoid the error does not restore the intended behavior.

## Bookkeeping that never contributes to the answer

Yue Liu and coauthors' [paper, Code 1][liu] presents a simplified generated
`getMinDistance` function that assigns an index but never reads or returns it.
A short excerpt, omitting surrounding code:

```python
min_index = -1
# ...
min_index = i
# ...
return min_diff
```

**Review:** Establish whether that state contributes to the contract. For this
function, remove redundant assignments. A caller requiring an index could instead
justify returning one. Native lint supports the review, but temporary variables
are not universally wrong. This is a minor maintainability issue, not a security
incident. The paper concerns an older model and benchmark setting.

Sources were checked on 2026-10-14. We did not re-execute the complete original
programs. Reconstructions are labeled and claims remain attributed. Do not copy
an example into a new product and treat it as that product's acceptance contract.
Use the [maintainability exercise](maintainability-exercise.md) for a credible
follow-up change. Accept different correct structures. These are teaching cases,
not hidden tests or proof that the new guidance improves an agent.

[anthropic]: https://www.anthropic.com/engineering/harness-design-long-running-apps
[fastapi]: https://fastapi.tiangolo.com/tutorial/path-params/#order-matters
[liu]: https://arxiv.org/html/2307.12596v2#S2.SS2
