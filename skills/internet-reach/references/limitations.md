# Reach limitations

- Domain-scoped web search finds indexed public pages. It does not prove that
  a private account feed or an unindexed post exists.
- Reddit, YouTube, Instagram, and LinkedIn can return a login wall, a consent
  page, an anti-bot page, or a JavaScript shell. Use the user-controlled,
  headless Zen `Agent` profile for the rendered page when its bridge is
  configured.
- GitHub can use `gh` for private repositories only when the user's existing
  `gh` session is authenticated. The helper never handles tokens.
- RSS/Atom feeds are read-only and may omit content that a site's web page
  displays.
- A HAR capture is session evidence, not a portable API or credential store.
  Keep cookies, authorization values, request bodies, and response bodies out
  of logs and the catalog.
- A browser bridge is bound to the machine and the isolated `Agent` profile.
  Keep one headless process as the profile owner and one active harness
  connection at a time. Set `ZEN_BIN` and
  `INTERNET_REACH_AGENT_PROFILE` per machine; never copy the profile. Kagent or
  another remote harness cannot reach a local bridge through localhost unless
  the user deliberately exposes a secured endpoint. Never point it at the
  normal browsing profile.
