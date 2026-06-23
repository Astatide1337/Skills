# Catalogs

A catalog describes where skills come from. Currently only local directory catalogs are supported.

## Configuration

```yaml
catalogs:
  local:
    type: local
    path: ./skills

  personal:
    type: local
    path: /home/user/skills
```

## Activation

```bash
# Via CLI
skills-gateway run --catalog local

# Via environment variable
SKG_CATALOG=local skills-gateway run

# Via config file
active_catalog: local
```

## Catalog vs Profile

- A **catalog** defines *where* skills come from (source)
- A **profile** defines *which* skills are exposed (filter)

They work together: a catalog provides the skill set, a profile filters it.

## Current Limitations

- Only `local` type is supported (directory-based)
- Remote registry, OCI, and Git-based catalogs are planned but not yet implemented
- If a catalog path doesn't exist, validation fails

## Future Catalog Types

Planned but not yet implemented:
- `git` — Clone from a Git repository
- `oci` — Pull from an OCI registry
- `remote` — Fetch from a remote registry API
