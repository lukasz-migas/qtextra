## Working agreements

- ALWAYS use qtpy when working with qt-based tools
- ALWAYS add type annotations and follow the latest styling guidelines
- ALWAYS add at least minimal documentation to public facing functions
- ALWAYS ask for confirmation before adding new production dependencies
- ALWAYS try to be concise in documentation, commit messages, and PR descriptions
- TRY to add tests when working with functions
- TRY not to write super long descriptions in plan mode, where fewer words suffice
- NEVER try to author PRs or commits
- NEVER cheat in benchmarks
- NEVER try to be funny in documentation, commit messages, or PR descriptions


## Pull Requests

When creating PRs, do NOT include a "Test plan" section. The PR body should contain only a Summary section with bullet points describing what changed.

## Style Preferences

- Keep it simple, no over-engineering
- Prefer stdlib over external dependencies
- Numerical work should be done with numpy, numba or similar libraries, not with custom code
- Variables should have proper names, not single letters, unless in very specific contexts (e.g. loop indices)
- Tests should be fast and isolated
- No emojis in code or output (except commit messages)
- Never amend commits; always create new commits for fixes
- Never push or pull unless explicitly asked by the user
- **NEVER** use weird characters in documentation (e.g. use simple ',-)
- **NEVER merge pull requests.** Do not run `gh pr merge` or any equivalent. Only the user merges PRs. This is non-negotiable.
- **NEVER change git branches without explicit user confirmation**. Always ask before switching, creating, or checking out branches. This is non-negotiable.
