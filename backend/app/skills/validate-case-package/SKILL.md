---
name: validate-case-package
description: Apply deterministic quality gates to a teaching case package, including schema completeness, body length, objective alignment, classroom timing, repetition, discussion depth, factual sources, official visuals, trusted videos, and reviewer-score consistency. Use before saving, finalizing, or exporting a case package.
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
- Target about ten strongly relevant items in each resource group: factual sources, selected official visuals, recommended official visuals, and trusted videos. A verified shortage is a warning, never a reason to pad with irrelevant content.
- If visual assets are selected, require verified official provenance, HTTPS source pages, rights notices, unique IDs, no more than ten images, and a course-context research signature.
- Require video title, publisher, source page, playback URL, teaching use, HTTPS and an `official` or reviewed `trusted` level. Never accept invented view counts.
