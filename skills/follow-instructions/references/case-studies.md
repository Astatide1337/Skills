# Engineering decisions: worked cases

Load only the case matching a consequential decision. These are original
instructional exercises grounded in linked primary publications, documented
interfaces and code. They are development material, not industry transcripts,
successful agent trials or reserved transfer assessments. A documented source
supports its stated mechanism; it does not certify the exercise's outcome.

| Decision | Worked case | What to inspect |
| --- | --- | --- |
| Work crosses an interruption | [Resume acceptance and live state](../examples/interrupted-delivery.md) | Whether the resumed agent retains every acceptance point and refreshes changed evidence before continuing |
| A real form rejects input | [Implement recoverable errors](../examples/form-error-recovery.md) | Actual pixels, preserved input, error focus, keyboard correction and the saved result |
| Authorized PR/MR delivery reaches review or CI | [Continue through a failure and review finding](../examples/delivery-through-review.md) | The owning correction, final-head behavior and host gates, including an honest external approval gate |

Examples expose decisions and valid alternatives; they do not require their
architecture, styling, runtime or feature count. Use the linked owner skill for
the current contract. Keep assessment inputs and reference answers separate.

The earlier Jobmark pagination case is
[historical evidence at preview `233fb741`](https://github.com/Astatide1337/Skills/blob/233fb741431a41b22e865d9baaedf62a90bface9/skills/follow-instructions/examples/jobmark-pagination.md).
Its original failure, correction and CI links remain inspectable there. It is
not a current teaching standard, a new replay or evidence of this revision's
effectiveness.
