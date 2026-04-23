---
name: Bug report
about: Something that should work doesn't
labels: bug
---

## What happened

<!-- Short description of the unexpected behavior. -->

## What you expected

<!-- What should have happened instead? -->

## Reproduction

<!-- Minimal steps. If possible, include the exact `claude_desktop_config.json` snippet and the tool call that failed. -->

```jsonc
{
  "mcpServers": {
    "pm4py": { "command": "uvx", "args": ["pm4py-mcp"] }
  }
}
```

Tool call:

```
# e.g., "call ping" / "load_event_log with path=..."
```

## Environment

- `pm4py-mcp` version: <!-- `pip show pm4py-mcp` or `uvx pm4py-mcp --version` -->
- Client: <!-- Claude Desktop / Claude Code / Inspector / other -->
- OS: <!-- Windows 11 / macOS 14 / Ubuntu 22.04 -->
- Python: <!-- `python --version` -->

## Logs

<!-- Paste server stderr or Inspector output if available. Redact any sensitive paths. -->
