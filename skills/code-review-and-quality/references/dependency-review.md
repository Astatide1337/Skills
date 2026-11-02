# Dependency review

Use when adding or upgrading dependencies. Respect offline, network,
installation and command restrictions. Report unavailable external facts as
unknown.

## Before adding a dependency

Check whether the standard library or existing utilities already solve the
problem. If a new dependency is needed, inspect:

- bundle or runtime size;
- maintenance history and unresolved issues;
- known vulnerabilities, using the package manager's audit tool when authorized;
- license compatibility with the project.

## Before upgrading a dependency

1. Read the changelog and, for a major version, migration notes. A version
   number alone does not establish compatibility; patch releases can change
   behavior.
2. Upgrade one dependency or a small related group per change. This makes
   failures easier to isolate and changes easier to revert.
3. Verify that the relevant tests pass before and after the upgrade. Installation alone
   does not verify behavior. If coverage is missing, identify that gap and add
   a test before an authorized upgrade; a review-only task reports the gap.
4. Review the lockfile as well as the manifest. A direct upgrade can change
   many transitive dependencies.
5. Commit and review the generated lockfile. Do not edit it by hand.

For advisory triage, typosquatting or compromised maintainers, use
`security-and-hardening`. This reference covers the upgrade procedure;
security severity depends on the affected code and attack path.
