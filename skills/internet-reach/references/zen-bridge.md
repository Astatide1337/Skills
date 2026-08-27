# Headless Zen Agent bridge

Use a separate Zen process and profile named `Agent`. Never attach a bridge to
the user's normal Zen profile: an existing-session connection can navigate,
type, close tabs, and read that profile's data.

The configured local client bridge is Mozilla's Firefox DevTools MCP, pinned to
`0.10.1` and restricted to the `slim` read/interaction tool set. It connects
to one already-running headless `Agent` process on loopback:

```text
npx -y @mozilla/firefox-devtools-mcp@0.10.1 \
  --connectExisting \
  --marionettePort 2828 \
  --toolPreset slim
```

The headless process owns the isolated profile at
`${INTERNET_REACH_AGENT_PROFILE:-$HOME/.config/zen/Agent}` and is launched
separately from the normal Zen process with Marionette enabled. It has no
visible window. The binary and profile are machine-local; set `ZEN_BIN` and
`INTERNET_REACH_AGENT_PROFILE` on another host rather than copying this
machine's profile. All three local harnesses use the same loopback owner; only
one harness may own it at a time. Do not start another worker against this
profile concurrently.

If the user wants authenticated Reddit, Instagram, or LinkedIn reads, they
must sign in themselves during the manual bootstrap below. Do not copy the
normal profile, export cookies, or ask the agent to enter credentials.

Launch or relaunch that isolated process with:

```text
ZEN_BIN="${ZEN_BIN:-$(command -v zen-browser || command -v zen || true)}"
AGENT_PROFILE="${INTERNET_REACH_AGENT_PROFILE:-$HOME/.config/zen/Agent}"
"${ZEN_BIN:?Set ZEN_BIN to the installed Zen/Firefox binary}" \
  --headless \
  --no-remote \
  --new-instance \
  --profile "$AGENT_PROFILE" \
  --marionette \
  --remote-debugging-port 9222 \
  --new-window about:blank
```

The upstream WebDriver cleanup may stop the connected `Agent` process when a
harness-owned MCP process exits. If that happens, relaunch only this process;
it does not affect normal Zen.

## Manual login bootstrap

Some identity providers, including Google, reject a login page when Marionette
or another automation signal is enabled. Do not bypass that protection or
weaken the account. Bootstrap the session manually in the isolated profile:

1. Close only the automated `Agent` window. Leave the user's normal Zen
   process alone.
2. Launch `Agent` without automation flags:

   ```text
   ZEN_BIN="${ZEN_BIN:-$(command -v zen-browser || command -v zen || true)}"
   AGENT_PROFILE="${INTERNET_REACH_AGENT_PROFILE:-$HOME/.config/zen/Agent}"
   "${ZEN_BIN:?Set ZEN_BIN to the installed Zen/Firefox binary}" \
     --no-remote \
     --new-instance \
     --profile "$AGENT_PROFILE" \
     --new-window https://accounts.google.com/
   ```

3. The user signs in themselves in that visible window. Never ask the agent
   to type a password, read a verification code, or approve a security prompt.
4. Close that normal `Agent` window completely, then relaunch the profile with
   the headless automation command above and reconnect the MCP client.

If the provider still blocks the session, keep the page unauthenticated or use
the provider's supported API/OAuth integration. Do not spoof a user agent,
disable account protections, or copy cookies into another profile.

Do not use the MCP server's self-launch mode against this profile while the
shared process is running. A second worker would race the profile lock and
could invalidate the authenticated session.

Use only bounded navigation, snapshots, text/attribute queries, and ordinary
search-field interaction explicitly requested by the user. Do not enable
arbitrary script execution, privileged Firefox access, network-body capture,
password reads, or account writes.

If the bridge is not exposed by the active harness, keep public search links
and report only the affected rendered read as unavailable. Do not install or
enable a bridge silently during an ordinary search.
