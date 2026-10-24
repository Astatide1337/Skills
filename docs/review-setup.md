# Enable cross-model pull request review

Merge the review-guideline PRs first. Keep `main` protected so Claude applies
root `REVIEW.md` includes; Skills main was unprotected at the 2026-10-24 readback.
Jobmark main was protected. Review settings below are owner actions, not changes
made by this PR.

## Codex on GitHub

Connect Skills and Jobmark to Codex. In [Codex Code review settings](https://chatgpt.com/codex/settings/code-review),
select each repository and turn on **Automatic review** under **Review code**.
Choose **All PRs**, or **Follow personal preferences** with **Personal preferences
→ Automatic review** on. Use **Review trigger** to select reviews on PR creation
and new pushes. A manual request is `@codex review`.

Codex reads the applicable `AGENTS.md`. These settings are documented in
[Review GitHub pull requests with Codex](https://learn.chatgpt.com/docs/third-party/github).

## Claude Code Review

The hosted review service requires a Claude Team or Enterprise organization.
As its Owner, open **Admin settings → Claude Code → Code review**, turn on
**Allow code review**, connect GitHub, install the Claude GitHub App for the two
repositories, select them and click **Finish**. On each repository's **Edit**
row, set **Review runs → After every push** and **Review level → Standard**.
**Manual (@claude review)** is a lower-cost alternative; use `@claude review
always` to subscribe one PR. Configure a spend limit before broad automatic use.

Claude reads `REVIEW.md`; its root `@AGENTS.md` include shares the concise rules
with Codex. The include is expanded when read from a protected branch. The local
`/code-review` command is separate and reads `CLAUDE.md` rather than `REVIEW.md`.
See [setup](https://code.claude.com/docs/en/code-review-setup) and
[customization](https://code.claude.com/docs/en/code-review-customize).

## Rutgers / GitLab note

Keep this manual until separately approved: `codex exec` can review an MR diff
in a read-only CI job, or a local `/code-review --comment` workflow can post
through `glab`. Adapt the GitHub-specific plugin before using it with GitLab;
do not assume it speaks `glab`. Every Rutgers write still requires approval.
