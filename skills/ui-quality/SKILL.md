---
name: ui-quality
description: Use this skill whenever designing, implementing, changing, or reviewing a user interface, layout, styling, responsive behavior, theme, visual state, or interaction. Inspect the existing product and real domain language first, then iterate against the rendered UI rather than judging source code alone. Capture and inspect screenshots during the work; when motion, animation, scrolling, drag/drop, video, or other temporal interaction matters, record it and watch the recording before accepting the result.
---

# UI Quality

Build against the rendered product, not an imagined interface.

## 1. Understand the existing product

Before changing UI:

- open the relevant existing screens;
- inspect the existing components, tokens, typography, spacing, and interaction patterns;
- identify the real product/domain terminology from code and existing copy;
- understand the user's requested visual/product intent.

Do not invent labels, categories, metrics, product concepts, or terminology simply to make the UI feel complete.

## 2. Preserve design language

Reuse established patterns unless the task explicitly changes them:

- components;
- typography scale;
- spacing rhythm;
- border radius and surface treatment;
- color/token usage;
- icon style;
- form behavior;
- navigation patterns.

Do not introduce a new visual system for a local change.

## 3. Implement the smallest coherent change

- Solve the requested experience.
- Avoid decorative elements that do not serve hierarchy or interaction.
- Do not saturate the UI with a brand/accent color.
- Keep copy concise, specific, and natural.
- Prefer clear domain language over generic AI-generated product wording.

## 4. Inspect the real interface

After implementation:

1. launch/open the actual app;
2. navigate to the changed state;
3. use the changed controls;
4. capture screenshots;
5. inspect the screenshots yourself;
6. correct visible problems;
7. repeat until the interface holds together.

Use the available `agent-browser` workflow for browser inspection in this environment; do not substitute the Playwright CLI. Respect the configured documentation/domain allowlist. If the real interface cannot be opened or captured, report that verification gap instead of claiming visual completion.

## 5. Check relevant state combinations

Exercise the states affected by the change. Include applicable combinations of:

- desktop and mobile;
- supported light/dark modes;
- supported themes;
- anonymous and meaningful authenticated roles;
- default, hover, focus, active, selected, and disabled;
- empty, loading, populated, validation-error, and server-error;
- short, long, and overflowing content;
- keyboard navigation and visible focus.

Do not mechanically test irrelevant combinations; cover the states the changed UI can realistically enter.

## 6. Inspect visual quality

Check screenshots for:

- hierarchy and focal point;
- alignment and spacing;
- typography and readable line lengths;
- color and contrast;
- clipping, overflow, unexpected scroll;
- responsive behavior;
- consistency with neighboring screens;
- duplicated or unnecessary visual elements;
- awkward copy or invented terminology;
- excessive density or excessive whitespace.

A UI can be technically valid and still be visually wrong.

## 7. Verify motion and interaction with video

When behavior changes over time:

- record the complete interaction or animation;
- watch the full recording;
- inspect start and end states;
- inspect timing, easing, continuity, layout shifts, jank, clipping, and accidental flashes;
- repeat after corrections.

Do not claim motion quality from screenshots or source code alone.

## 8. Preserve accepted choices

If the user rejects a visual change, treat the correction as a constraint for the current task. Do not reintroduce the rejected pattern elsewhere unless explicitly requested.

When comparing options or iterating, preserve parts the user already accepted instead of redesigning the whole screen.

## Final acceptance

Before accepting the UI:

- the requested experience is visibly present;
- screenshots have been captured and inspected;
- relevant interaction states have been exercised;
- motion has been recorded and watched when applicable;
- responsive/theme behavior is sound where applicable;
- no obvious regression was introduced in neighboring UI.

Use `verify-work` for the final completion claim when the task includes implementation or delivery beyond visual quality.
