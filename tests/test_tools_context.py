"""Phase 3 Slice 3 — domain context tool unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pm4py_mcp.errors import WorkspaceError
from pm4py_mcp.tools.context import (
    ContextNotFound,
    _clear_all_for_tests,
    _get_context_for_prompts,
    get_domain_context,
    set_domain_context,
)


@pytest.fixture(autouse=True)
def _clear_contexts() -> None:
    _clear_all_for_tests()


def test_set_domain_context_inline_text() -> None:
    result = set_domain_context("SOP: every order must have a Place Order event.")
    assert result["name"] == "default"
    assert result["source"] == "inline text"
    assert result["size_bytes"] > 0
    assert result["approx_tokens"] >= 1
    assert result["warning_large"] is False
    assert result["stored_context_count"] == 1


def test_set_domain_context_custom_name() -> None:
    result = set_domain_context("Glossary entry: triage = initial assessment.", name="glossary")
    assert result["name"] == "glossary"
    assert result["stored_context_count"] == 1


def test_set_domain_context_from_file(tmp_path: Path) -> None:
    sop_file = tmp_path / "sop.md"
    sop_file.write_text("# SOP\n\nStep 1: register. Step 2: triage.", encoding="utf-8")

    result = set_domain_context(str(sop_file))
    assert result["source"].startswith("file: ")
    assert result["size_bytes"] == len(sop_file.read_text(encoding="utf-8").encode("utf-8"))

    stored = get_domain_context()
    assert "Step 1: register" in stored["content"]


def test_set_domain_context_file_takes_precedence_over_inline(tmp_path: Path) -> None:
    """If the text_or_path is a readable existing file, it's loaded, not treated as inline."""
    f = tmp_path / "ctx.txt"
    f.write_text("from file", encoding="utf-8")
    result = set_domain_context(str(f))
    stored = get_domain_context()
    assert stored["content"] == "from file"
    assert result["source"].startswith("file: ")


def test_set_domain_context_oversize_raises() -> None:
    huge = "x" * 25_000
    with pytest.raises(WorkspaceError, match="exceeds"):
        set_domain_context(huge)


def test_set_domain_context_warning_large_flag() -> None:
    mid = "y" * 12_000  # > 10k warn, < 20k cap
    result = set_domain_context(mid)
    assert result["warning_large"] is True


def test_set_domain_context_overwrite_same_name() -> None:
    set_domain_context("first", name="shared")
    result = set_domain_context("second", name="shared")
    assert result["stored_context_count"] == 1
    stored = get_domain_context("shared")
    assert stored["content"] == "second"


def test_set_domain_context_too_many_raises() -> None:
    for i in range(16):
        set_domain_context(f"ctx-{i}", name=f"name-{i}")
    with pytest.raises(WorkspaceError, match="Too many"):
        set_domain_context("overflow", name="one-too-many")


def test_get_domain_context_roundtrip() -> None:
    set_domain_context("hospital triage SOP text")
    result = get_domain_context()
    assert result["name"] == "default"
    assert result["content"] == "hospital triage SOP text"
    assert result["size_bytes"] > 0
    assert result["approx_tokens"] >= 1


def test_get_domain_context_unknown_name_raises() -> None:
    with pytest.raises(ContextNotFound):
        get_domain_context("never-set")


def test_get_context_for_prompts_returns_none_when_empty() -> None:
    assert _get_context_for_prompts() is None


def test_get_context_for_prompts_returns_stored_content() -> None:
    set_domain_context("prompt-visible context")
    assert _get_context_for_prompts() == "prompt-visible context"


def test_get_context_for_prompts_named() -> None:
    set_domain_context("other", name="named")
    assert _get_context_for_prompts("named") == "other"
    assert _get_context_for_prompts("default") is None
