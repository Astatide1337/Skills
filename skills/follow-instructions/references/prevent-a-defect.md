# Prevent a confirmed defect

Start with the first confirmed mistake, whether discovered while implementing,
reported by the user, or found during review. Identify the violated behavior
and an input or transition that should still work. Distinguish defects from
changed requirements, preferences, and unconfirmed suspicions.

**Find the condition that makes the mistake possible.** Trace the actual
failure through the system, including its build, configuration, deployment
and use when relevant. Ask what could be removed, derived, isolated, reordered
or made atomic so that a future contributor no longer has to remember a rule.
Two hand-edited configurations can drift; generate both from one source.
Rebuilding after verification can ship different bytes; promote the tested
artifact by digest. A partial write can leak intermediate state; publish it
atomically. A misleading default or irreversible UI action may call for a
different interaction. A narrower API is another option when callers supply
a fact the system already knows. Choose from the cause, including options
outside these examples. Show the old and proposed paths, the failure each
allows or excludes, compatibility with legitimate use, and the cost.

**Choose the enforcer.** Make the in-scope repair where the failure originates. Check for bypasses,
including other writers, legacy data, manual steps and alternate build paths.
When the operation must stay expressible, reject invalid input at the boundary,
use a compiler or lint diagnostic, or put a behavioral regression on the
project's normal check path. If a check already caught this mistake, use it.
If it was disconnected, exercise the repaired invocation. Several findings
can share an enforcer when it covers each failing path.

**Calibrate the repair.** Exercise the original defect on the old version or
a targeted faulty variant. Check that the fixed version accepts a different
valid case and satisfies the original outcome. In the existing review or PR,
identify the enforcer, the paths exercised, and its limit: prevented by construction within the stated boundary, rejected at runtime,
or detected by the named check. If prevention
remains open, identify the missing evidence or change and its owner. For
read-only work, propose the repair and the checks that would distinguish it
from a symptom patch. Broader migrations remain proposals outside the task's
authority.

Keep executable rules in the affected project. Use a short instruction for
decisions that still need judgment, such as who decides whether an exception
is acceptable. Retire duplicate mechanical guidance after its replacement
covers the same intent.
