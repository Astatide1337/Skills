# Worked exercise: a form error the user can recover from

Use when implementing validation and recovery in a real form. This is an
**original instructional exercise** grounded in the GOV.UK Design System's
[error-summary guidance and code](https://design-system.service.gov.uk/components/error-summary/)
and [rendered example](https://design-system.service.gov.uk/components/error-summary/default/).
GOV.UK specifies an error summary, matching field messages, links to invalid
answers and focus movement. The team-settings task below is invented; it is not
a GOV.UK implementation claim or evidence that a particular visual style wins.

## Problem, owner and implementation

A user edits a team name and contact address, then submits an invalid address.
The server rejects the save. A red toast and a passing validator unit test are
tempting: they show the error exists, but not that the user can find and correct
it. Clearing the form after rejection also destroys useful work.

Inspect the existing submit handler, validation response and form-state owner.
Reuse their error representation and input state. For a multi-field page, render
an actionable summary and a message beside the invalid field. The primary source
demonstrates a link to the specific input, for example
`<a href="#full-name-input">Enter your full name</a>`, with a matching input ID
and associated error text. Use the application's own labels and field IDs.

An original sketch of the state decision is:

```js
const submitted = readFields(form);
const result = await updateTeam(submitted);
if (!result.ok) {
  renderRejectedForm(submitted, result.errors);
  document.getElementById("form-errors").focus();
  return;
}
showSavedTeam(result.team);
```

This is not a drop-in implementation: the error container must be focusable,
field messages must be associated with controls, and existing framework state
must remain authoritative. If a component already manages focus, use it rather
than adding a second focus handler. Unexpected server failures need their own
recovery message; do not mislabel them as invalid user input.

## Evidence to obtain

Open the relevant reference image with a vision-capable tool using
[`web-interface`](../../web-interface/SKILL.md), then compare hierarchy and error
discoverability in the rendered candidate. A link or successful fetch alone is
not image inspection. Use the available T3 browser to submit the actual form,
inspect preserved input and error focus, activate the error link by keyboard,
correct the address, and observe the saved value through a fresh read. Check
that a denied write changes no saved value. Preserve revision/instance identity
and distinguish these observations from validator-unit results.

## Valid alternative and limits

A compact inline editor with one visible field may use an accessible inline
error and direct focus instead of a page summary when the product's conventions
and user path support it. GOV.UK's required summary is its design-system rule;
it is not a universal architecture. A dark operational panel can satisfy the
same recovery outcome without copying GOV.UK's appearance.

Screenshots support visual assessment. They do not prove keyboard behavior,
persistence, authorization or screen-reader output. Test those claims through
the relevant interface, and report untested assistive technology explicitly.
