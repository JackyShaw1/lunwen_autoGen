# Quality Gate

## Severity

- `error`: blocks finalization and export because the package violates a hard requirement.
- `warning`: allows saving a draft but requires teacher review.
- `info`: records a non-blocking improvement.

## Hard requirements

- Background, narrative, and decision point are non-empty.
- Visible body characters are 95%–105% of the target.
- At least two roles and five discussion questions exist.
- Questions cover at least three cognitive levels.
- Every objective ID appears in the alignment matrix with case section, activity, and assessment.
- Reviewer scores are 1–5 and the overall score matches their rounded mean.
- Internal production notes such as `【学科注释】` never appear in student-facing body fields.
- Source-grounded cases contain at least five fully traceable sources; each source ID is cited in the body.
- Selected visuals and videos contain complete provenance, HTTPS links, unique IDs and no unreviewed source.

## Quality warnings

- Long paragraphs are repeated or substantially duplicated.
- The narrative contains instructional meta-language or reveals the answer.
- The decision point has no action, trade-off, or accountable decision-maker.
- The teaching flow exceeds the available duration or provides no explicit minutes.
- Alignment uses generic labels with no observable assessment.
- Any resource group with fewer than eight reviewed items warns against the target of about ten; missing resources are preferable to unrelated padding.

Never convert a warning into a passing score merely because all JSON fields exist.
