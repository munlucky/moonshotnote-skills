# Public Safety Checklist

Before publishing a generated skill:

- No full source text in tracked files.
- No long verbatim passages from third-party material.
- No absolute local home paths from Windows, macOS, or Linux.
- No emails, phone numbers, resident registration numbers, account IDs, or private names unless explicitly intended for publication.
- No API keys, bearer tokens, passwords, database URLs, cookies, private keys, or secret-like values.
- No generated `output/`, `private-source/`, cache, model, or virtual environment directories tracked by git.
- All public graph rows have `public_safe: true`.
- All public graph rows have source refs.
- Manifest states whether the package is public-sanitized.
- README install commands point to the intended public repository and skill name.

If any item fails, fix before commit or push.
