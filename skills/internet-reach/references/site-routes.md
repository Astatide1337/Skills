# Site search routes

Use a native web-search tool with the domain filter first. These templates are
the browser fallback when the harness needs a concrete URL.

| Source | Domain filter | Native URL |
| --- | --- | --- |
| Reddit | `reddit.com` | `https://www.reddit.com/search/?q=QUERY` |
| YouTube | `youtube.com` | `https://www.youtube.com/results?search_query=QUERY` |
| Instagram | `instagram.com` | `https://www.instagram.com/explore/search/keyword/?q=QUERY` |
| LinkedIn | `linkedin.com` | `https://www.linkedin.com/search/results/all/?keywords=QUERY` |

`QUERY` must be URL-encoded as one value. Never interpolate raw user text into
HTML or JavaScript. The helper's `search-url` command performs this encoding
and emits JSON with the source, URL, and domain.

Search-engine results are the default for Instagram and LinkedIn because their
native search pages commonly require a signed-in session. Use the native URL
when the user asks for current in-app results and the Zen bridge is connected.
For Reddit, prefer the domain-filtered search when the user wants discussions;
the native page is useful for the user's own saved or account-scoped results.
For YouTube, the native page is usually the best public video index.

After navigation, wait for the result list, take a bounded accessibility
snapshot or text extraction, and keep only links whose host matches the
requested source. Do not treat recommendations, ads, or a login prompt as
matching results.
