# Contributing Guidelines

Thank you for contributing to the BUSY Bar repository!

## Branching Strategy & Workflow
- **Trunk-Based Development**: `main` is protected and represents production-ready state.
- **Branch Naming**:
  - `feat/<short-description>`: New features for `busybar_kit` or tools
  - `fix/<short-description>`: Bug fixes
  - `docs/<short-description>`: Documentation updates
  - `app/<slug>`: Adding or updating an app in `apps/`
  - `chore/<short-description>`: Maintenance, CI, dependencies
- **PR & Merge Policy**: Pull requests require review. Squash-and-merge is enforced; feature branches are deleted upon merge.
- **Versioning**:
  - `busybar_kit` follows Semantic Versioning via git tags (`v0.x.y`).
  - Apps in `apps/<slug>` are versioned in their respective `manifest.yaml` files.

## Commit Message Format
Write clear, functional, and descriptive commit messages describing what changed and why. Avoid rigid conventional commit prefixes (like `feat(kit):`).

Examples:
- Add priority ladder and 409 jittered backoff to busybar_kit
- Sanitize weather description strings in buienradar-alarm
- Document OpenAPI endpoint map and transport prefix differences

## Secret Prevention & Remediation
**NEVER commit `config/devices.toml`, `.env`, API tokens, or access keys.**

### Secret Leak Remediation Runbook
If a secret is accidentally committed:
1. **Immediate Invalidation**:
   - For LAN access key: Open device local web UI over USB / IP, go to settings, and rotate/regenerate the API access key.
   - For Cloud token: Log in to `https://cloud.busy.app`, revoke the compromised token, and generate a new one.
2. **History Cleanup**:
   - Rewrite git history (e.g. using `git filter-repo` or BFG Repo-Cleaner) to remove the committed secret from all commits and tags.
3. **Notify Maintainers**: Report the leak immediately so any shared environment tokens can be rotated.

## Code Style & Testing
- Pre-commit hooks (`gitleaks`, `ruff`, `ruff-format`) must pass before committing.
- Run `pytest` locally to verify changes. Tests in `tests/` guard `busybar_kit` and contract compliance with the OpenAPI spec.
