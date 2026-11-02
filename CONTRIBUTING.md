# Contributing guidelines

Development workflow, multi-SDK setup, and verification standards for local development in this repository. All contributors and autonomous agents must adhere to the canonical rules in [AGENTS.md](AGENTS.md).

## Execution architecture decision gate

Before scaffolding or writing code for any new application or integration, evaluate and agree on the target architecture:

- **Remote host-side integration (`busybar_kit` + `busylib-py` or Node host):** Use when orchestrating multiple BUSY Bar devices, integrating with local desktop state or enterprise webhooks, requiring heavy compute or memory (>512 KiB), accessing the full HTTP API, or running scheduled background daemons over Wi-Fi or USB.
- **Native on-device JavaScript application (`busy-tools` + `@busy-app/busy-lib`):** Use when the app must run standalone on the BUSY Bar inside the firmware's JerryScript engine, respond to physical hardware buttons and the rotary encoder (`listen("input")`), launch from the on-device APPS menu, or package self-contained settings (`src/appmeta/settings.json`) and media assets into `/ext/user_assets/<app_id>`.
- **Hybrid architecture:** Use only when an on-device interactive app explicitly requires a companion host service to pre-process external feeds or manage settings via `/api/apps/settings`.

## Multi-SDK and submodule setup

This repository combines a shared Python host library (`src/busybar_kit/`) with non-recursive upstream reference submodules under `vendor/`:

- **Python host environment:** Create and use the local virtual environment (`.venv`). Install dependencies via `pip install -e ".[dev]"`. Never install packages globally on the host system.
- **Node 24 toolchain for on-device apps:** On-device JavaScript/TypeScript applications built with `@busy-app/cli` (`busy-cli`) and `@busy-app/create-app` require Node 24 (`>=24 <26`). Node 26 is unsupported.
- **Reference submodules:** Keep `vendor/busylib-py`, `vendor/busylib-ts`, and `vendor/busy-tools` non-recursive (`recurse = false` in `.gitmodules`). Use them as local read-only sources of truth for SDK types, capability parity, `@shared/*` runtime helpers, and bundler behavior.
- **Upstream sync workflow:** To pull upstream SDK or OpenAPI updates, run `git submodule update --remote`, check specification drift with `.venv/bin/python tools/sync_openapi.py --check` (or `--update` followed by `.venv/bin/python tools/gen_endpoint_map.py`), update `vendor/busybar-openapi/PROVENANCE.md`, and run the verification suite.

## Git workflow and incremental commits

- **Incremental functional commits:** Break work into small, bisectable functional milestones (schema updates, `busybar_kit` modules, app features, test coverage) and commit each milestone as soon as it is verified. Do not accumulate large monolithic diffs across unrelated subsystems.
- **Commit message format:** Write direct, descriptive commit summaries in plain English stating what changed and why. Do not use conventional commit prefixes (`feat:`, `fix:`, `chore:`).
- **Worktree hygiene:** Treat each git worktree as an isolated workspace with its own local dependencies and build artifacts. Do not use `git stash` to move uncommitted work across worktrees. Transfer changes strictly via explicit branch merges or pull requests, and prune inactive worktrees after merging.

## Verification and testing requirements

Run the verification suite before every commit:

- **Python linting and formatting:** `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` must pass with zero warnings or errors.
- **Unit and contract tests:** `.venv/bin/pytest` must pass. Any modification to `src/busybar_kit/` requires corresponding unit and OpenAPI contract test updates in `tests/`.
- **On-device JS app verification:** When working on an on-device JS/TS application in `apps/`, verify that `npm run typecheck` and `npm run build` succeed, `src/main.ts` has no exports, `src/appmeta/manifest.json` matches the directory ID and minimum `api_version`, and only the 18 sandboxed HTTP API endpoints are used.

## Data privacy and secret management

- **Zero secrets in version control:** Never commit `config/devices.toml`, `.env`, production credentials, API tokens, or LAN access keys. Redact tokens and Wi-Fi credentials from all log outputs.
- **Client confidentiality:** Never reference specific client or external partner names in tracked code, configuration templates, documentation, or `AGENTS.md`. Place client-specific work exclusively in the git-ignored `apps/_clients/` workspace.
- **Secret leak remediation:** If a credential is accidentally committed, immediately rotate the LAN access key in the device web UI (or revoke the Cloud token at `https://cloud.busy.app`) and purge the secret from git history using `git filter-repo`.
