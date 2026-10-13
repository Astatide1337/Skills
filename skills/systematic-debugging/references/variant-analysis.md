# Variant analysis after a confirmed defect

Use when a supported failure mechanism could recur in sibling code. Do not
launch a repository-wide hunt before understanding the original defect.

1. State the mechanism as a relationship: untrusted identifier reaches an
   unscoped query, retry repeats an effect, or caller bypasses validation.
2. Inspect sibling owners and call paths using native symbol/text search first.
   Search for the mechanism's dataflow and missing invariant, not only identical
   lines. Structural search is optional when many repeated shapes justify it.
3. Inspect each candidate in context. Alternate guards, lifecycle or inputs can
   make a match harmless; distinguish confirmed instances from hypotheses.
4. Exercise the same boundary with independent expected results for confirmed
   instances. Preserve owner/non-owner checks for authorization defects.
5. Repair in-scope variants and rerun relevant regression checks. Report broader
   work separately; a discovered issue does not authorize unrelated changes.

Method provenance: original synthesis informed by Trail of Bits'
[variant-analysis technique](https://github.com/trailofbits/skills/tree/main/plugins/variant-analysis).
No upstream plugin, scanner or mandatory audit process is installed.
