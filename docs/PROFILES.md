# Profiles

A profile is a named working set of skills. When a profile is active, only those skills are exposed via MCP tools and resources.

## Configuration

```yaml
profiles:
  repo-review:
    skills:
      - pr-risk-review
      - codebase-map

  ops:
    skills:
      - log-triage
      - incident-summary
```

## Activation

```bash
# Via CLI
skills-gateway run --profile repo-review

# Via environment variable
SKG_PROFILE=repo-review skills-gateway run

# Via config file
active_profile: repo-review
```

## Behavior

- If no profile is selected, **all valid skills** are exposed
- `skills_list` and `skills_search` respect the active profile
- `skills_inspect` for skills not in the profile returns not-found
- `skill_read` for skills not in the profile returns invalid path
- `/inventory` shows the `active_profile` and list of profiles

## Profile Validation

- If `active_profile` references a profile not defined in `profiles`, validation fails
- If a profile references a skill that doesn't exist in the skills directory, a warning is logged and the readiness check reports the issue
