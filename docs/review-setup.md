# Enable cross-model pull request review

Merge the review-guideline PRs first. Local Claude review is the default; no
hosted review service or billing upgrade is required. Account settings remain
owner-controlled.

## Codex on GitHub

Connect Skills and Jobmark to Codex. In [Codex Code review settings](https://chatgpt.com/codex/settings/code-review),
select each repository and turn on **Automatic review** under **Review code**.
Choose **All PRs**, or **Follow personal preferences** with **Personal preferences
→ Automatic review** on. Use **Review trigger** to select reviews on PR creation
and new pushes. A manual request is `@codex review`.

Codex reads the applicable `AGENTS.md`. These settings are documented in
[Review GitHub pull requests with Codex](https://learn.chatgpt.com/docs/third-party/github).

## Local Claude review

In the feature-branch checkout, start Claude Code and run an explicit diff target:

```text
/code-review main...HEAD
```

For a stacked PR, substitute its actual base branch for `main`. Omit `--fix`
and `--comment` to keep the result local and read-only. With no explicit target,
Claude may compare against the upstream feature branch and miss already-pushed
commits. The root `CLAUDE.md` imports `AGENTS.md`, so the same review guidelines
apply to local Claude and Codex. Local review uses the existing Claude session's
plan allowance; no hosted-review plan is needed. See
[local review](https://code.claude.com/docs/en/code-review-local) and
[instruction imports](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools).

The separate hosted Claude Code Review service is optional and is not part of
this setup. `REVIEW.md` retains the shared rules if it is enabled later; its
imports require a protected base/default branch. See
[hosted review customization](https://code.claude.com/docs/en/code-review-customize).

## Rutgers / GitLab note

Rutgers writes require explicit approval. `codex exec` can review an MR diff
in a read-only CI job, or local `/code-review` can inspect it without posting. Any `--comment`/`glab` write requires separate approval.
