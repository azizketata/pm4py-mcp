"""Slice 1 — workspace directory tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pm4py_mcp.errors import WorkspaceError
from pm4py_mcp.workspace import (
    DEFAULT_SUBDIR,
    ENV_VAR,
    derived_path,
    ensure_workspace,
    workspace_dir,
)


def test_default_dir_under_home(monkeypatch: pytest.MonkeyPatch) -> None:
    # The autouse fixture sets PM4PY_MCP_WORKSPACE; undo that here.
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert workspace_dir() == (Path.home() / DEFAULT_SUBDIR).resolve()


def test_env_var_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "custom-ws"
    monkeypatch.setenv(ENV_VAR, str(target))
    assert workspace_dir() == target.resolve()


def test_env_var_expands_tilde(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, "~/my-custom-ws")
    assert workspace_dir() == (Path.home() / "my-custom-ws").resolve()


def test_ensure_creates_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "fresh"
    monkeypatch.setenv(ENV_VAR, str(target))
    assert not target.exists()
    result = ensure_workspace()
    assert target.is_dir()
    assert result == target.resolve()


def test_ensure_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "ws"
    monkeypatch.setenv(ENV_VAR, str(target))
    ensure_workspace()
    ensure_workspace()  # second call must not raise
    assert target.is_dir()


def test_derived_path_normalizes_extension() -> None:
    with_dot = derived_path("render", ".png", unique=False)
    without_dot = derived_path("render", "png", unique=False)
    assert with_dot == without_dot


def test_derived_path_unique_by_default() -> None:
    a = derived_path("render", "png")
    b = derived_path("render", "png")
    assert a != b


def test_derived_path_rejects_path_separator() -> None:
    with pytest.raises(WorkspaceError):
        derived_path("sub/dir/render", "png")


def test_derived_path_returns_absolute() -> None:
    p = derived_path("render", "svg")
    assert p.is_absolute()
