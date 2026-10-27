---
name: explain-diff-html
description: Use when the user asks for a rich explanation of a code change, diff, branch, or PR. Produces HTML output.
triggers:
  - "$explain-diff-html"
  - "explain this diff"
  - "explain this code change"
  - "rich PR explanation"
  - "diff를 자세히 설명해줘"
  - "변경사항을 HTML로 설명해줘"
  - "PR 설명 페이지를 만들어줘"
outputArtifacts:
  - JSON content spec
  - self-contained HTML explanation page
policyClauseIds:
  - explain-diff-html.policy.use-when
  - explain-diff-html.policy.routing
  - explain-diff-html.policy.hard-stops
  - explain-diff-html.policy.output-contract
policyDigest: 670a19b9eb173cb7774854b3a0fe3e9ee87d854732894a4342dbf48299c45bdc
layer: documentation
deepReferences:
  - references/compatibility-contract.md
  - scripts/render.py
---

# Explain Diff HTML Skill

## Use When

Use this skill when the user asks for a rich, interactive explanation of a code change, diff, branch, or pull request and wants a self-contained HTML page.

## Route Away

- If the requested destination is a Notion page, state that this skill produces HTML and do not claim to create a Notion page.
- Route to `moonshot-architecture` when the user is asking for a new architecture decision rather than an explanation of an existing change.
- Route to `moonshot-orchestrator` or `moonshot-phase-runner` when the user asks to implement the change instead of explain it.

## Role

- explain the existing system relevant to the change for readers with different levels of familiarity
- make the core intuition concrete with small examples and diagrams
- provide a high-level, ordered walkthrough of the changed code
- test understanding with five medium-difficulty interactive multiple-choice questions

## Procedure

1. Inspect the relevant diff, branch, or pull request and broadly explore surrounding code before writing the explanation.
2. Prepare the sections `Background`, `Intuition`, `Code`, and `Quiz`. Use concrete toy data and a small number of reusable HTML diagram families.
3. Write a small JSON content spec containing `title`, optional `subtitle`, `slug`, `sections`, and five quiz questions with `correct` options.
4. Run `python scripts/render.py <spec.json>` from the skill directory or use an explicit `-o <output.html>` destination. Let the renderer own the page scaffolding, CSS, JavaScript, table of contents, quiz-option randomization, and date-prefixed filename.
5. Use raw HTML in section `html` fields: `<pre>` for code, `.diagram`/`.flow`/`.box`/`.box.fail` for diagrams, `.callout` for definitions or edge cases, and plain `<table>` for comparisons.
6. Return the generated spec and HTML paths, and briefly state any source or rendering limitation.

## Hard Stops

- Do not hand-write the repeated HTML/CSS/JavaScript page boilerplate when `scripts/render.py` can render it.
- Do not describe behavior that was not grounded in the inspected diff or surrounding source.
- Do not use ASCII diagrams; use the renderer's HTML diagram classes.
- Do not copy secrets, credentials, private tokens, or unrelated personal data into the explanation.
- If the diff or renderer is unavailable, report the blocked evidence instead of inventing a complete explanation.

## Output Contract

- Produce one JSON content spec and one self-contained HTML page.
- Include Background, Intuition, Code, and Quiz sections, with five interactive quiz questions.
- Preserve the requested diff/branch/PR scope and distinguish observed facts from interpretation.
- Return absolute or workspace-relative output paths plus skipped or blocked reasons.

## References

- Source recipe: https://gist.github.com/ankitg12/8e808d387799de4e9839bc393f8e6405
- Local renderer: `scripts/render.py`
- Compatibility anchors: `references/compatibility-contract.md`
