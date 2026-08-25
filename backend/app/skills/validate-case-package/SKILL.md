---
name: validate-case-package
description: Apply deterministic quality gates to a teaching case package, including schema completeness, body length, objective alignment, classroom timing, repetition, discussion depth, official-visual provenance, and reviewer-score consistency. Use before saving, finalizing, or exporting a case package.
---

# Validate Case Package

Treat validation as a release gate, not a writing suggestion.

## Workflow

1. Read `references/quality-rubric.md` for severity and acceptance rules.
2. Run `scripts/validate_case_package.py` with the package and task context.
3. Return structured issues containing `severity`, `code`, `message`, and `path`.
4. Block finalization and export on `error` issues. Preserve `warning` issues for teacher review.
5. Never let an LLM override deterministic counts, required fields, timing totals, or score arithmetic.

## Acceptance

- Count visible characters across background, narrative, and decision point, excluding whitespace.
- Require 95%–105% of the requested body length.
- Require at least five questions and three cognitive levels.
- Require every learning objective in the alignment matrix.
- Detect exact or near-exact repeated long paragraphs.
- Require reviewer overall score to equal the five-dimension mean within rounding tolerance.
- If visual assets are selected, require verified official provenance, HTTPS source pages, rights notices, unique IDs, no more than six images, and a course-context research signature.
