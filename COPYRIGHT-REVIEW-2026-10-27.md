# Copyright and provenance review — 2026-10-27

Scope: the four skill directories added in the local working tree. This is an
inventory and evidence review, not a legal opinion or proof that every item is
cleared. Installation in an account root does not itself establish the right
to publish its contents. None of the four is cleared for public release until
the applicable unresolved items below are resolved.

## diagram-design

- The installed skill contains 287 files. Compared with the public upstream
  `cathrynlavery/diagram-design` at commit
  `97d795138448f6a739a0cebc3d9beb37a42077f1`, 274 match after line-ending
  normalization, 13 differ, and none is local-only. The 13 differences have not
  been independently traced to their authors or commits.
- Upstream license: MIT, Copyright (c) 2025 Cathryn Lavery. The full notice is
  preserved in `skills/diagram-design/LICENSE`. Source:
  https://github.com/cathrynlavery/diagram-design/blob/97d795138448f6a739a0cebc3d9beb37a42077f1/LICENSE
- `references/primitive-icons.md` identifies Tabler Icons (MIT), Simple Icons
  (CC0), Devicon (MIT), and log-z/logos (MIT). Their license texts are included
  under `skills/diagram-design/licenses/`. These are project-level notices;
  the exact version and provenance of each individual icon are not established.
- Five icon entries explicitly request license verification: hop, pentaho,
  dagster, sas, and stata. They and copies that may occur in other assets need
  individual source, license, and trademark review or replacement. Brand
  marks may have trademark restrictions independently of copyright licenses.
- Examples link to externally hosted Google Fonts. Font files are not bundled;
  generated output and any later font redistribution require separate review.
- Pending: trace the 13 differences and all embedded assets, resolve the five
  direct-fetch icons, and verify downstream notices before publication.

## explain-diff-html

- The installed entrypoint identifies an ankitg12 Gist as the source recipe;
  the renderer identifies a geoffreylitt Gist. The former is shown as a fork
  of the latter. No explicit license was found in the inspected Gist pages.
- Sources: https://gist.github.com/ankitg12/8e808d387799de4e9839bc393f8e6405
  and https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524
- Pending: establish the license and provenance of the instructions, renderer,
  and template; obtain permission or replace material that cannot be cleared.
  A public Gist or a source attribution alone is not a redistribution license.

## humanize-korean

- The account-root copy has no identified license or authorship record.
  `references/scholarship.md` and `references/ai-tell-taxonomy.md` contain
  material described as verbatim from a report and academic sources; the report,
  rights holder, extent of licensed use, and citation context were not verified.
  Baseline data also cites external research.
- Pending: identify the original report and rights holders, check each quoted
  or derived passage and dataset, and remove or replace material without a
  confirmed basis for public redistribution. Do not assume citation alone is
  permission. Verify authorship of the remaining instructions and scripts.

## ebook-to-md

- The account-root copy has no identified license or authorship record. It
  references external `agent-browser` and `ocr-document-processor` projects;
  these dependencies are not included in this repository. Their current terms
  and the authorship of the copied scripts still need verification.
- The skill requires authorized access and prohibits bypassing access controls.
  Rights to the processed ebook remain a separate issue for each user and work.
- Pending: establish the rights to all nine copied files and verify the terms
  and availability of the referenced dependencies.

## Review method and limits

Enumerated all files in the four skill directories; searched text for license,
source, attribution, copyright, direct quotation, external references, and
common path/credential indicators; checked the upstream diagram repository
and license; and compared every installed diagram file by normalized SHA-256.
This does not establish authorship of unmarked text or scripts, verify every
remote asset, perform a legal analysis of every quotation, or guarantee that a
later version of an external dependency has the same terms.

## Local validation

The skill-creator validator accepts diagram-design, humanize-korean, and
ebook-to-md. It rejects explain-diff-html because its installed frontmatter
contains extra policy and routing keys. Those keys are retained pending a
compatibility review. The diagram flowchart example passed its self-check;
the ebook browser inspection was exercised in dry-run mode only. On this
Windows host, validation required Python UTF-8 mode because the default console
encoding could not read or print some characters.
