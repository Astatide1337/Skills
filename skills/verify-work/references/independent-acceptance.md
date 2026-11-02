# Independent acceptance and calibration

Use this reference for substantive acceptance decisions, disputed results or
changes to a verifier. Keep the existing status and receipt formats. The
instructions describe how to assess evidence; they do not implement isolation
or a new verification service.

## Expectations

Derive required outcomes from the request, accepted decisions and authoritative
application contracts. The engineer may propose checks. Have them assessed
separately to confirm that they test the requirements, then freeze the acceptance
inputs where the implementer cannot edit them. Tests written during implementation
remain useful, but they cannot alone establish independent acceptance.

Hidden cases test the stated discoverable contract, never secret requirements.
Reference similarity is required only when fidelity is part of the brief.
Use pre-change behavior to protect unaffected features, not to preserve the
reported bug.
A material expectation correction is explicit, versioned and independently
reviewed. Reassess baseline and candidate under the same corrected contract.

## Observations and protection

Use the application's supported checks or a CLI version fixed for the task,
with the runtime's existing isolation controls. Run candidate code without unrelated secrets or privileges.
Protect check discovery, runner logic, acceptance inputs and authoritative outputs.
A read-only prompt, separate directory, hash or candidate-generated receipt does
not establish that protection. Exercise harmless owned canaries where protection
is claimed. Local filesystem containment does not prove isolation of browsers,
connected services, network access, CI or deployment effects.

Record the actual source tree/build, requirement version, relevant dependencies,
instance and environment, auth/data mode, check identity and expected/observed
results. Inspect underlying output instead of only an agent's conclusion. A
commit is insufficient for a dirty tree or different running build. Refresh
affected checks and review after a candidate change. Preserve evidence after
owned cleanup. Development login is not proof of real CAS authentication.

If a required protection or observation is unavailable, try supported recovery
and identify the requirement that remains unverified. Fixture success does not
establish application behavior, independent review or production readiness.

## Judgment

A fresh reviewer starts with the requirement, actual artifact and direct results
before the author's justification. Different models are optional and do not
remove shared blind spots. Findings identify the issue, affected requirement or
quality criterion, evidence and resolution condition. Separate blockers from
optional refinements. An unconventional valid solution is not a defect.

Required functional, visual, usability, security and maintainability properties
cannot be averaged into one passing score. Judge the whole applicable artifact,
not only a textual checklist. An agent-run journey does not establish real-user
benefit. Visual quality needs agreed reference examples and inspection of the rendered
result. Keep review within its budget and do not invent new requirements.

## Check the checker

In disposable, authorized copies, present a known-valid result, a different valid
alternative, a meaningful behavioral defect, and missing/stale evidence. Confirm
acceptance or rejection for the intended reason. A syntax error does not show
that an authorization or persistence defect will be caught. A verifier that
rejects every result also fails.

To assess a new judge of visual quality, prose, plans or issue usefulness, use
accepted and rejected examples, unseen cases and multiple successful styles.
Include the intended reader's actual judgments when available. Invented teaching
examples do not establish the reader's taste. Allow disagreement and insufficient
evidence as results.

Investigate and report disagreements with the reader's demonstrated acceptance
before trusting the judge or claiming improvement. Reader preference helps
assess usefulness; it does not override facts or safety requirements. Record
false rejection as well as false acceptance. Once a control has been exposed
during development, do not describe it as held out in future evaluations.

## Parent acceptance

For delegated implementation with executable acceptance, select and review the
task checker before dispatch. Locate the complete reviewed agent-gates bundle:
`agent_gates.py` and its sibling `test_integrity.py`. Use a Skills checkout or an
authorized hook installation; installing skill folders alone does not install
that bundle. Its [command reference](https://github.com/Astatide1337/Skills/blob/main/global-instructions/hooks/README.md#parent-acceptance)
lives in the source repository.

At return, run from the current candidate workspace, replacing the paths below:

```sh
printf '{}\n' | python3 /path/to/hooks/agent_gates.py accept \
  python3 /trusted/task_acceptance.py
```

Supply the checker's required JSON context instead of `{}` when it needs one.
Exit 0 accepts; exit 1 rejects; exit 2 means the checker is unavailable. If the
bundle or checker is absent, recover it within authority or retain the unmet
check. An ended worker run or a Stop hook's exit 0 cannot
replace that check. Resolve rejected obligations and recheck after repairs;
keep required judgment and independent review separate from executable checks.

## Decision

Accept only when every applicable required outcome is established, required
independent review covers the final candidate, evidence is current and delivery
stays authorized. Missing, failed, stale and required-but-unavailable results
cannot pass. Genuinely inapplicable checks have a reason. Local acceptance, PR
readiness, deployed behavior and reliability over time are separate claims.
Repair and recheck within the declared budget. At a real permission, capability
or budget limit, preserve the best verified result and state which checks remain
unmet. Do not claim readiness.

## Worked counterexample

The UI reports a successful save, but a fresh read returns the old value. A
success-toast assertion passes the wrong implementation. A check of the actual
persisted value rejects it. If the check denies every edit, the valid-owner
control rejects the checker's apparent success. A new candidate reusing old
screenshots remains unverified even when both screenshots look identical.
