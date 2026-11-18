# Prevent a confirmed defect

Start with the first confirmed mistake, whether discovered while implementing,
reported by the user, or found during review. Identify the violated behavior
and an input or transition that should still work. Distinguish defects from
changed requirements, preferences, and unconfirmed suspicions.

**Find the owner.** Trace the failing path and other callers that can make the
same mistake. Who already knows the value, owns the transition, or has authority
to decide? If changing an API, type, or representation can exclude the whole
class, show the current call and its replacement, affected callers, and any
migration cost. For example, when a server already knows who answered a
request, derive authorship there instead of accepting an author from each
caller. Check what happens to legacy records whose author is unknown.

**Choose the enforcer.** Make the in-scope repair at that owner. Check other
writers, stored data and external inputs that can bypass a typed caller.
When the operation must stay expressible, reject invalid input at the boundary,
use a compiler or lint diagnostic, or put a behavioral regression on the
project's normal check path. If a check already caught this mistake, use it.
If it was disconnected, exercise the repaired invocation. Several findings
can share an enforcer when it covers each failing path.

**Calibrate the repair.** Exercise the original defect on the old version or
a targeted faulty variant. Check that the fixed version accepts a different
valid case and satisfies the original outcome. In the existing review or PR,
identify the enforcer, the paths exercised, and its limit: impossible through
this API, rejected at runtime, or detected by the named check. If prevention
remains open, identify the missing evidence or change and its owner. For
read-only work, propose the repair and the checks that would distinguish it
from a symptom patch. Broader migrations remain proposals outside the task's
authority.

Keep executable rules in the affected project. Use a short instruction for
decisions that still need judgment, such as who decides whether an exception
is acceptable. Retire duplicate mechanical guidance after its replacement
covers the same intent.
