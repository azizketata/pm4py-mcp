# Contributing to pm4py-mcp

Thanks for your interest in `pm4py-mcp`. This project is in **Phase 0** (walking skeleton). Contributions are welcome, but the tool surface is intentionally small and the architectural decisions in [`CLAUDE.md`](CLAUDE.md) are locked — please raise an issue before proposing changes to them.

## Developer Certificate of Origin (DCO)

**All commits must be signed off.** This project does **not** require a Contributor License Agreement; instead, it relies on the [Developer Certificate of Origin 1.1](https://developercertificate.org/) — the same mechanism used by the Linux kernel, Docker, and PM4Py upstream.

Sign off each commit with:

```bash
git commit -s -m "your message"
```

This appends a `Signed-off-by: Your Name <your@email>` trailer certifying that you have the right to submit the contribution under the project's AGPL-3.0-or-later license. The DCO GitHub App will block PRs with unsigned commits.

If you forgot to sign off, amend with:

```bash
git commit --amend --signoff
git push --force-with-lease
```

## Development setup

**Requirements:** Python 3.10–3.13 and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/azizketata/pm4py-mcp.git
cd pm4py-mcp
uv sync --extra dev
```

## Running the server locally

Launch the server over stdio and call tools with the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector uv run pm4py-mcp
```

Open the Inspector URL it prints, click **Tools → ping → Call**, and expect `pong pm4py-mcp <version>`.

## Tests

The project uses a **four-layer testing pyramid**. Run all layers with:

```bash
uv run pytest
```

| Layer | Marker | What it catches |
|-------|--------|-----------------|
| Unit | none | Tool logic bugs |
| In-process `ClientSession` | `in_process` | Schema / protocol registration |
| Stdio subprocess | `subprocess` | PATH, CWD, encoding, startup ordering |
| MCP Inspector CLI | nightly CI only | Spec-compliance drift |

Run a single layer with `uv run pytest -m in_process` etc.

## Code style

- **Formatter:** `ruff format`
- **Linter:** `ruff check`
- **Type checker:** `mypy src`

Run all three before pushing:

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src
```

Or install pre-commit hooks once and forget about it:

```bash
uv run pre-commit install
```

## Architectural guardrails

Before opening a PR, skim the **Locked architectural decisions** section in [`CLAUDE.md`](CLAUDE.md) and the **What not to do** section. The most common rejection reasons:

1. Returning event logs / DataFrames / large blobs from tools (blows Claude Desktop's ~1 MB response cap). Always return **handles + summaries + file paths**.
2. Overloading a tool to accept both XES logs and OCEL 2.0 objects. Use the parallel `ocel_*` namespace.
3. Wrapping more of PM4Py's surface. The tool surface is capped at ~15–25 workflow verbs on purpose — "dumping 43 tools into the context window" is an anti-pattern for MCP.
4. Adding `pip install pm4py-mcp` instructions. MCP users configure servers via JSON; `uvx` is the documented path.

## Commit message conventions

Short, imperative, scope-prefixed where helpful:

```
ping: include Python version in response
tests: add stdio subprocess roundtrip on Windows
ci: bump matrix to include 3.14
```

Breaking changes: prefix with `!` (e.g. `tools!: rename discover_petri_net signature`).

## Reporting bugs

Use [GitHub Issues](https://github.com/azizketata/pm4py-mcp/issues) with a reproducible example. For security-sensitive reports, see [`SECURITY.md`](SECURITY.md) — do not open a public issue.

## Licensing of contributions

By signing off your commits you agree that your contribution is licensed under **AGPL-3.0-or-later**, the same license as the rest of the project (and as PM4Py upstream). If your employer owns the copyright, ensure they allow DCO sign-off on your behalf.
