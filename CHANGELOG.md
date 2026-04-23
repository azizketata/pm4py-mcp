# Changelog

All notable changes to `pm4py-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Governance files: `LICENSE` (AGPL-3.0-or-later), `CONTRIBUTING.md` (with DCO requirement), `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`.
- Package scaffolding: `pyproject.toml` using hatchling, `src/pm4py_mcp/` layout.
- Phase 0 walking skeleton: single `ping` tool served over stdio via FastMCP.
- Four-layer testing pyramid: unit, in-process `ClientSession`, stdio subprocess, MCP Inspector CLI (nightly).
- CI matrix: Python 3.10–3.13 × Ubuntu / macOS / Windows.
- PyPI Trusted Publishing workflow.

## [0.0.1] - TBD

First PyPI release claiming the `pm4py-mcp` name. No user-facing functionality beyond the `ping` health-check tool.

[Unreleased]: https://github.com/azizketata/pm4py-mcp/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.0.1
