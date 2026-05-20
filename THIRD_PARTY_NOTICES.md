# Third Party Notices

This repository contains the `moonshotnote-ocr` Agent Skill source code.
The skill scripts are licensed under the repository license. Runtime OCR
dependencies are not vendored in this repository; they are installed locally by
`skills/moonshotnote-ocr/scripts/setup.ps1` from PyPI or compatible package
indexes.

Review the licenses of these dependencies before redistributing a bundled
environment, container image, binary package, or proprietary product that
includes them.

## Direct Runtime Dependencies

| Package | Version Constraint | License | Purpose |
| --- | --- | --- | --- |
| `paddlepaddle` | `==3.2.2` | Apache Software License | PaddleOCR runtime backend |
| `paddleocr` | `==3.4.1` | Apache License 2.0 | Korean-first OCR engine |
| `surya-ocr` | `==0.17.1` | GPL-3.0-or-later | Document OCR, layout, reading order, table recognition |
| `transformers` | `<5` | Apache 2.0 License | Surya-compatible model/runtime dependency |
| `pillow` | unpinned | HPND | Image loading and conversion |
| `opencv-python` | unpinned | Apache 2.0 | Image processing |
| `numpy` | unpinned | BSD-style license | Numeric/image array processing |
| `pandas` | unpinned | BSD 3-Clause License | Tabular output and processing support |

The license values above were checked from installed Python package metadata in
the development environment used to prepare this skill. Transitive dependencies
may add additional license obligations.

## GPL Dependency Notice

`surya-ocr` is licensed as GPL-3.0-or-later. This repository does not vendor or
redistribute Surya model files or Python packages, but the setup script installs
`surya-ocr` into the user's local skill environment. If you redistribute a
prebuilt environment containing `surya-ocr`, review GPL-3.0-or-later
requirements for your distribution model.

## Model Files

OCR model files are downloaded or cached by the upstream OCR libraries at
runtime. They are intentionally excluded from this repository. Model files may
carry separate licenses or use terms from their upstream providers.

## Generating a Full Local Dependency Report

After running setup, generate a fuller environment-specific dependency report
with tooling such as:

```powershell
.\.venv\Scripts\python.exe -m pip install pip-licenses
.\.venv\Scripts\python.exe -m piplicenses --format=markdown --with-urls --with-license-file
```

Use the generated report for release or redistribution decisions.
