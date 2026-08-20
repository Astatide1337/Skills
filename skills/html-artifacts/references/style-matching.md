# Style matching

Match the source's design logic, not its incidental pixels.

Inspect supplied artifacts and the relevant codebase for typography, spacing,
color roles, border treatment, density, icon style, data-display conventions,
and interaction patterns. Prefer existing CSS variables, tokens, and reusable
assets when they can be embedded safely. Do not claim a match from a logo and
brand color alone.

Identify the load-bearing traits that make the source recognizable. Preserve
those first, then adapt the composition to the artifact's reading task. A dense
operations report may need the product's type and semantic colors but not its
application navigation. A presentation may use the same visual language at a
different scale.

When no source style exists, choose a direction based on audience and genre:

- evidence reports favor clear hierarchy, restrained status colors, and dense
  but scannable tables;
- architecture explainers favor stable spatial relationships and legible
  labels over decoration;
- comparisons favor aligned structures and visible differences;
- option explorations favor a contact sheet or repeated frame so alternatives
  can be compared under identical conditions;
- annotated reviews keep comments visibly anchored to the exact region, line,
  or state they discuss.

Avoid generic card grids when the material is a document, ornamental metrics,
and visual novelty that obscures provenance. Inspect one wide and one narrow
render against the source traits, not only against general polish.
