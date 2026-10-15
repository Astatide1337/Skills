# Sourced visual references and documented AI failures

Use when a composition decision needs a concrete reference. The Apple, Stripe
and Linear images were fetched and their actual pixels inspected on
**2026-10-15**. The documented AI contrasts retain the earlier 2026-10-14
inspection; they are optional diagnostic material. Positive selections are our
assessment for the stated purpose, not a universal certificate or user approval.

## Choose by task, not by brand or similarity

| ID | Role | Useful distinction |
| --- | --- | --- |
| `apple-music` | Positive reference | Content hierarchy and subordinate navigation |
| `linear-sidebar` | Dense operational navigation | Comparable before/after states; selected destination remains distinct |
| `stripe-payment-layouts` | Positive alternatives | The same form in three valid disclosure patterns |
| [GOV.UK recovery](#govuk-validation-and-recovery) | Live browser example | Related error summary, field feedback and recovery target |
| `ai-solo-opening` | Negative case | Decorative emphasis that competes with starting a task |
| `ai-solo-editor` | Negative case | Working-area allocation and small controls |
| `ai-harness-editor` | Better alternative, not a gold standard | More usable allocation of canvas and tools |

Do not compare unrelated products with one aesthetic score. Match the interaction,
content and density. References inform choices, not mandatory styles. Screenshots
cannot establish keyboard operation, accessibility, persistence or product benefit.

## Positive references

### Apple Music: content leads

[Source: Apple Newsroom, June 9, 2025][source-apple]

![Apple Music with a grouped sidebar and content-led album sections][image-apple-music]

**Inspect in a candidate:** Can a user distinguish navigation, the main content
groups and the persistent action at the intended viewport?

**Assessment:** Section headings, aligned artwork and quieter navigation establish
a clear content hierarchy. Useful for media-rich interfaces, not a universal
workspace layout. The artwork is meaningful content rather than unrelated decoration.

**Limits:** This is a product-marketing still. Do not copy device framing, Apple
branding, album art or translucency into an unrelated product. Preserve the principle
of emphasis, not the assets or visual skin. Interaction was not tested here.

### Stripe: several valid form compositions

[Source: Stripe Payment Element documentation][source-stripe]

![Stripe tabs and two accordion payment layouts][image-stripe-payment-layouts]

**Inspect in a candidate:** Compare grouping with realistic options and labels,
then exercise selection, pending and error states in the actual implementation.

**Assessment:** Aligned fields and grouped payment choices make the selected
operation distinct. All three arrangements are valid alternatives under different
space and interaction requirements. The lesson is not that tabs always beat cards.

**Limits:** This is a component reference, not a complete application's design.
Check real labels, focus, error behavior and contrast in the implementation. No
payment integration or extra dependency is justified merely by this reference.

### Linear: dense operational navigation

[Source: Linear, March 12, 2026][source-linear]

![Linear sidebar before and after its refresh, with the same navigation items][image-linear-sidebar]

**Decision:** The comparison keeps the destination and content comparable. The
selected Inbox stays prominent while repeated icons and inactive navigation
recede. Use it when a workspace's navigation competes with its working area.

**Inspect in a candidate:** Can the user locate the current destination and the
next useful action without every row demanding equal attention? Check the actual
text contrast and target size before reducing either.

**Limits:** A publisher's annotated still is not usability evidence. This crop
shows navigation, not a complete operational screen; its subdued inactive text
may be unsuitable for another audience, theme or display. A light, bordered or
more colorful hierarchy can be equally valid.

### GOV.UK: validation and recovery

[Source: GOV.UK error-summary guidance][source-govuk]. Open the
[live multi-field recovery example][browser-govuk-recovery] in the attached T3
browser and inspect its rendered pixels. This is a browser reference, not an
image bundled with the skill or fetched by the image script.

**Decision:** One page-level summary points to the erroneous year field; a
matching inline error identifies the correction while the valid day and month
remain present. This deliberately plain direction is useful for transactional
forms where finishing the task matters more than visual novelty.

**Inspect in a candidate:** Submit invalid input, follow the summary link by
keyboard, correct the field, and check that other entered values survive. Inspect
focus and the resulting state, not just the red border.

**Limits:** GOV.UK's exact wording, typography and service conventions are not
requirements for another product. The published component example demonstrates
an error state and focus target, not backend validation or successful submission.
Its URL and page content were checked on 2026-10-15; the audit environment's T3
snapshot timed out, so no screenshot inspection is claimed here. If the browser
cannot render it, use a task-relevant inspected reference and record the gap.

## Documented AI-output cases

[Anthropic's experiment report][source-anthropic] explicitly identifies these as
AI-generated outputs. The critique concerns specific artifacts, not presumed AI
authorship from fonts or color choices. The source also reports runtime defects,
but those are attributed observations, not our execution of the original apps.

### Solo opening screen

![AI-generated opening screen with competing create actions][image-ai-solo-opening]

**Finding:** Branding and an oversized empty panel dominate while two similar
create actions compete. Auxiliary text is faint. This is a task-emphasis problem,
not proof that retro styling or duplicate entry points are always wrong.

### Solo sprite editor

![AI-generated editor leaving much of the viewport unused][image-ai-solo-editor]

**Finding:** The working panels stop far above the bottom of the viewport while
controls remain small and dense. Allocate space to the actual editing task before
adding decoration. Neon colors alone do not determine quality.

### A better AI-generated alternative

![AI-generated alternative with a larger working canvas and grouped tools][image-ai-harness-editor]

**Finding:** The canvas uses more height and tools are grouped distinctly. This
is a useful contrast, not a perfect reference. Small controls still need testing.
The source reports remaining workflow problems. Better appearance is not complete
acceptance, and AI-generated does not mean automatically bad.

## Local viewing, attribution and limits

These are attributed source links, **not redistributed third-party image or font
files**. For a local vision tool, explicitly fetch selected images into a task-owned
directory with the [reference fetcher](../scripts/fetch_references.py):

```sh
python3 /path/to/installed/web-interface/scripts/fetch_references.py --list
python3 /path/to/installed/web-interface/scripts/fetch_references.py \
  --id apple-music --id stripe-payment-layouts --output /path/to/task-reference-dir
```

Use the actual installed skill path; from this checkout it is
`skills/web-interface/scripts/fetch_references.py`.
`--all` selects the six listed image sources, including the optional AI contrasts.
Repeat the command with the same directory to reuse an intact copy: the receipt
URL, file signature and SHA-256 must still match. Cache reuse is task-local; it
does not prove the publisher has not changed a remote image. For a deliberate
source refresh, select a fresh task-owned directory. A changed URL, damaged file
or unrelated existing directory fails visibly instead of overwriting it. The
installer never fetches the network.
The fetcher contacts only the reviewed public hosts without browser credentials,
records byte hashes, cache reuse and failures, and does not assign an aesthetic
pass. If Pillow is already available, it decodes the image and rejects broken
bytes; otherwise the receipt says decoding was not checked. No dependency is
installed. Open the actual downloaded pixels with a vision-capable tool before
using them; a fetch or decode receipt is not evidence that the model saw them.
If decoding or viewing fails, keep that reference unavailable rather than judging
its caption. Local copies remain outside the repo.

Image ownership and applicable usage terms remain with the publishers. These
links are not a license to put their artwork in a shipped product. Source pages
and hosted bytes may change. A receipt establishes what was fetched, not that a
changed image matches this assessment or is licensed for redistribution.

The image fetcher was exercised against Apple, Stripe and Linear from an
isolated installation on 2026-10-15, followed by actual local-image inspection.
Offline tests cover cache integrity and failures, not future host availability.

These exposed teaching cases are not held-out evaluations. Use genuine product-
specific quality anchors and valid alternative styles before claiming transfer.

[source-apple]: https://www.apple.com/newsroom/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/
[source-stripe]: https://docs.stripe.com/payments/payment-element
[source-linear]: https://linear.app/now/behind-the-latest-design-refresh
[source-anthropic]: https://www.anthropic.com/engineering/harness-design-long-running-apps
[source-govuk]: https://design-system.service.gov.uk/components/error-summary/
[browser-govuk-recovery]: https://design-system.service.gov.uk/components/error-summary/linking-multiple-fields/
[image-linear-sidebar]: https://webassets.linear.app/images/ornj730p/production/b6d6be14c96978b10553cfb9205be1065087e793-3904x2720.png?auto=format&dpr=2&q=95
[image-apple-music]: https://www.apple.com/newsroom/images/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/article/Apple-WWDC25-macOS-Tahoe-26-Apple-Music-250609_big.jpg.large.jpg
[image-stripe-payment-layouts]: https://b.stripecdn.com/docs-statics-srv/assets/pe_layout_example.525f78bcb99b95e49be92e5dd34df439.png
[image-ai-solo-opening]: https://www.anthropic.com/_next/image?q=75&url=https%3A%2F%2Fwww-cdn.anthropic.com%2Fimages%2F4zrzovbb%2Fwebsite%2F23c98f1d7ae720bfb39190d50e0706c03b177ad8-1999x1320.png&w=3840
[image-ai-solo-editor]: https://www.anthropic.com/_next/image?q=75&url=https%3A%2F%2Fwww-cdn.anthropic.com%2Fimages%2F4zrzovbb%2Fwebsite%2F24472c85629a6c82a092f25def4a659042be1f7c-1999x1010.png&w=3840
[image-ai-harness-editor]: https://www.anthropic.com/_next/image?q=75&url=https%3A%2F%2Fwww-cdn.anthropic.com%2Fimages%2F4zrzovbb%2Fwebsite%2Fc05aa3ef8daaf0ef3d0dba66d6480ab753e9cbaa-1999x1007.png&w=3840
