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

- 서로 다른 숙련도의 독자를 위해 변경과 관련된 기존 시스템을 설명합니다.
- 작은 예시와 다이어그램으로 핵심 직관을 구체화합니다.
- 변경된 코드를 이해하기 쉬운 순서로 high-level walkthrough로 정리합니다.
- 이해 여부를 확인하는 중간 난이도의 객관식 퀴즈 다섯 개를 제공합니다.

## Procedure

1. 설명을 쓰기 전에 관련 diff, 브랜치 또는 PR과 주변 코드를 폭넓게 확인합니다.
2. `Background`, `Intuition`, `Code`, `Quiz` 섹션을 준비하고, 구체적인 toy data와 재사용 가능한 소수의 HTML 다이어그램을 사용합니다.
3. `title`, 선택적 `subtitle`, `slug`, `sections`, 정답 선택지가 포함된 퀴즈 다섯 개를 담은 작은 JSON content spec을 작성합니다.
4. 스킬 디렉터리에서 `python scripts/render.py <spec.json>`을 실행하거나 `-o <output.html>`을 지정합니다. 페이지 골격, CSS, JavaScript, 목차, 퀴즈 선택지 무작위화, 날짜 접두 파일명은 renderer가 소유합니다.
5. 섹션의 `html` 필드에는 raw HTML을 사용합니다. 코드에는 `<pre>`, 다이어그램에는 `.diagram`/`.flow`/`.box`/`.box.fail`, 정의나 예외에는 `.callout`, 비교에는 일반 `<table>`을 사용합니다.
6. 생성된 spec과 HTML 경로를 반환하고, 소스 또는 렌더링 제약을 짧게 명시합니다.

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

- 원본 recipe: https://gist.github.com/ankitg12/8e808d387799de4e9839bc393f8e6405
- 로컬 renderer: `scripts/render.py`
- 호환성 기준: `references/compatibility-contract.md`
