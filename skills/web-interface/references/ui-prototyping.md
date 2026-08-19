# UI Prototyping

Read this only when the user explicitly wants to compare visual directions
before committing to one. A UI prototype answers one design question; it is
not production code.

1. State the decision question and success criteria. Default to two or three
   variants; cap at five.
2. Prefer variants on an existing screen or host surface so they use real
   navigation, data, density, and surrounding design language. Create a
   throwaway route only when no plausible host exists.
3. Make variants structurally different: change hierarchy, layout, or primary
   affordance, not just colors or copy. Keep real mutations out of the
   prototype unless the question explicitly concerns mutation behavior.
4. Make the active variant shareable and reload-stable, for example with the
   host framework's query parameter conventions. Keep any switcher clearly
   marked and unavailable in production.
5. Capture the chosen direction and why. Fold the winner into normal code;
   remove losing variants and the switcher rather than letting prototype code
   become a permanent second UI.
