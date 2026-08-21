---
name: design-instructional-plan
description: Design observable learning objectives, progressive discussion questions, time-bounded classroom activities, and objective-to-evidence alignment for teaching cases. Use when generating or reviewing objectives, discussion designs, instructor guides, assessment methods, or classroom timing.
---

# Design Instructional Plan

Build the teaching design from the learner outcome backward.

## Workflow

1. Preserve the teacher's topic, course, audience, and stated intent.
2. Select a reasoning framework from `references/objective-writing.md`.
3. Write three observable objectives at increasing cognitive levels. Read `references/bloom-taxonomy.md` when choosing verbs.
4. Build questions from case evidence rather than generic course knowledge. Read `references/discussion-ladder.md`.
5. Map every objective to a case section, activity, and observable assessment. Read `references/alignment-rules.md`.
6. Keep the sum of activity minutes within the available class time.

Use `scripts/generate_objectives.py` for deterministic objective suggestions. Do not replace teacher-edited objectives unless explicitly requested.

## Acceptance

- Use observable verbs; avoid “了解、熟悉、掌握”.
- Give every objective at least one evidence source and assessment.
- Cover at least three cognitive levels across five or more questions.
- Make each question cite a role, event, datum, constraint, or decision from the case.
- Keep the class plan executable within the configured duration.
