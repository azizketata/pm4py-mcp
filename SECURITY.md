# Security Policy

## Supported versions

`pm4py-mcp` is pre-1.0 software in Phase 0. Only the latest published version on PyPI receives security fixes.

| Version | Supported |
|---------|-----------|
| latest `0.x` on PyPI | Yes |
| anything older | No |

## Reporting a vulnerability

**Do not open a public GitHub issue for security reports.**

Please report vulnerabilities privately via one of:

1. **GitHub private vulnerability reporting** (preferred): <https://github.com/azizketata/pm4py-mcp/security/advisories/new>
2. **Email:** mohamed.aziz.ketata@gmail.com

Include, if possible:

- A description of the issue and its impact
- Steps to reproduce (or a proof-of-concept)
- Affected version(s) / commit(s)
- Any suggested mitigation

## Response SLA

- **Acknowledgment:** within 72 hours of receipt.
- **Triage and severity assessment:** within 7 days.
- **Fix or mitigation timeline:** communicated after triage; typically 30 days for high-severity issues.

We will coordinate a disclosure timeline with the reporter and credit you in the advisory unless you prefer to remain anonymous.

## Scope

In scope:

- The `pm4py-mcp` server code and its published PyPI artifacts
- Tool input validation, path traversal, and workspace sandboxing
- Dependency vulnerabilities we can mitigate by pinning or patching

Out of scope:

- Vulnerabilities in PM4Py itself — report those upstream at <https://github.com/process-intelligence-solutions/pm4py/security>
- Vulnerabilities in the MCP SDK — report to <https://github.com/modelcontextprotocol/python-sdk/security>
- Vulnerabilities in the MCP client (Claude Desktop, Claude Code, Inspector) — report to the respective vendors

## Safe harbor

Good-faith security research conducted in compliance with this policy is welcome. We will not pursue legal action against researchers who follow the private-disclosure process above.
