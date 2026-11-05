# Engineering decisions: worked cases

Read the case that matches the decision you need to make. These are original
instructional exercises grounded in linked primary publications, documented
interfaces and code. They are development material, not industry transcripts,
successful agent trials or held-out evaluation tasks. A documented source
supports its stated mechanism; it does not certify the exercise's outcome.

| Decision | Worked case | What to inspect |
| --- | --- | --- |
| Work crosses an interruption | [Resume acceptance and live state](../examples/interrupted-delivery.md) | Whether the resumed agent retains every acceptance point and refreshes changed evidence before continuing |
| A real form rejects input | [Implement recoverable errors](../examples/form-error-recovery.md) | Actual pixels, preserved input, error focus, keyboard correction and the saved result |
| Authorized PR/MR delivery reaches review or CI | [Continue through a failure and review finding](../examples/delivery-through-review.md) | The owning correction, final-head behavior and host gates, including an honest external approval gate |

Use the examples to compare decisions and valid alternatives. Their
architecture, style, runtime and feature count are not requirements. Use the
linked owner skill for the current contract. Keep assessment inputs and
reference answers separate.
