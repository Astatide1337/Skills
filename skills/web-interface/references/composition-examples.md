# Sourced visual references and documented AI failures

Use when a composition decision needs a concrete reference. These replace the
uncalibrated, self-made editor illustrations. The five images below were opened
and visually inspected on **2026-10-14**. Positive selections are our assessment
for the stated purpose, not a universal certificate or Soham's approval.

## Choose by task, not by brand or similarity

| ID | Role | Useful distinction |
| --- | --- | --- |
| `apple-music` | Positive reference | Content hierarchy and subordinate navigation |
| `stripe-payment-layouts` | Positive alternatives | Form grouping and multiple valid disclosure patterns |
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

**Assessment:** Section headings, aligned artwork and quieter navigation establish
a clear content hierarchy. Useful for media-rich interfaces, not a universal
workspace layout. The artwork is meaningful content rather than unrelated decoration.

**Limits:** This is a product-marketing still. Do not copy device framing, Apple
branding, album art or translucency into an unrelated product. Preserve the principle
of emphasis, not the assets or visual skin. Interaction was not tested here.

### Stripe: several valid form compositions

[Source: Stripe Payment Element documentation][source-stripe]

![Stripe tabs and two accordion payment layouts][image-stripe-payment-layouts]

**Assessment:** Aligned fields and grouped payment choices make the selected
operation distinct. All three arrangements are valid alternatives under different
space and interaction requirements. The lesson is not that tabs always beat cards.

**Limits:** This is a component reference, not a complete application's design.
Check real labels, focus, error behavior and contrast in the implementation. No
payment integration or extra dependency is justified merely by this reference.

### Linear: supplementary design rationale, image inspection pending

[Linear's own design-refresh account][source-linear] explains navigation emphasis,
alignment and pruning unnecessary visual separation. It is useful supporting
rationale for operational interfaces.

Its [published sidebar comparison][linear-sidebar] could not be rendered through
the available image-retrieval route in the final verification pass. It is therefore
**not counted as a visually verified image or included in the fetcher's curated set**.
Inspect it in an available browser before using it as a visual anchor. Neither its
brand nor its captions are a substitute for seeing the artifact.

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
files**. For a local vision tool, explicitly fetch selected images into a fresh
run-owned directory with the [reference fetcher](../scripts/fetch_references.py):

```sh
python3 skills/web-interface/scripts/fetch_references.py --list
python3 skills/web-interface/scripts/fetch_references.py \
  --id apple-music --id stripe-payment-layouts --output /path/to/fresh-reference-dir
```

Resolve the script from its installed location when outside the Skills checkout.
`--all` selects all five inspected images. The installer never fetches the network.
The fetcher contacts only the reviewed public hosts without browser credentials,
records byte hashes and failures, and does not assign an aesthetic pass. Open the
actual downloaded pixels before using them. Local copies remain outside the repo.

Image ownership and applicable usage terms remain with the publishers. These
links are not a license to put their artwork in a shipped product. Source pages
and hosted bytes may change. A receipt establishes what was fetched, not that a
changed image matches this assessment or is licensed for redistribution.

The images were inspected through the web image viewer. Direct network access in
the coding container was unavailable, so the Python fetcher's live-origin path
was not exercised there. Its offline tests cover request and failure handling,
not availability from every future host. A download failure remains visible.

These exposed teaching cases are not held-out evaluations. Use genuine product-
specific quality anchors and valid alternative styles before claiming transfer.

[source-apple]: https://www.apple.com/newsroom/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/
[source-stripe]: https://docs.stripe.com/payments/payment-element
[source-linear]: https://linear.app/now/behind-the-latest-design-refresh
[source-anthropic]: https://www.anthropic.com/engineering/harness-design-long-running-apps
[linear-sidebar]: https://webassets.linear.app/images/ornj730p/production/b6d6be14c96978b10553cfb9205be1065087e793-3904x2720.png?auto=format&dpr=2&q=95
[image-apple-music]: https://www.apple.com/newsroom/images/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/article/Apple-WWDC25-macOS-Tahoe-26-Apple-Music-250609_big.jpg.large.jpg
[image-stripe-payment-layouts]: https://b.stripecdn.com/docs-statics-srv/assets/pe_layout_example.525f78bcb99b95e49be92e5dd34df439.png
[image-ai-solo-opening]: https://www.anthropic.com/_next/image?q=75&url=https%3A%2F%2Fwww-cdn.anthropic.com%2Fimages%2F4zrzovbb%2Fwebsite%2F23c98f1d7ae720bfb39190d50e0706c03b177ad8-1999x1320.png&w=3840
[image-ai-solo-editor]: https://www.anthropic.com/_next/image?q=75&url=https%3A%2F%2Fwww-cdn.anthropic.com%2Fimages%2F4zrzovbb%2Fwebsite%2F24472c85629a6c82a092f25def4a659042be1f7c-1999x1010.png&w=3840
[image-ai-harness-editor]: https://www.anthropic.com/_next/image?q=75&url=https%3A%2F%2Fwww-cdn.anthropic.com%2Fimages%2F4zrzovbb%2Fwebsite%2Fc05aa3ef8daaf0ef3d0dba66d6480ab753e9cbaa-1999x1007.png&w=3840
