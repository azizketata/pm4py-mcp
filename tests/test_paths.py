"""Unit tests for pm4py_mcp._paths.resolve_input_path."""

from __future__ import annotations

from pathlib import Path

import pytest

from pm4py_mcp._paths import ENV_HINT, resolve_input_path


def test_absolute_path_existing_file_returns_as_is(tmp_path: Path) -> None:
    f = tmp_path / "log.xes"
    f.write_text("x", encoding="utf-8")
    out = resolve_input_path(str(f), kind="Event log")
    assert out == f


def test_absolute_path_missing_raises_with_all_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_HINT, raising=False)
    ghost = tmp_path / "missing.xes"
    with pytest.raises(FileNotFoundError) as exc:
        resolve_input_path(str(ghost), kind="Event log")
    msg = str(exc.value)
    assert "Event log not found" in msg
    assert "input path:" in msg
    assert "server CWD:" in msg
    assert f"{ENV_HINT}: (not set)" in msg


def test_relative_path_under_cwd_resolves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = tmp_path / "log.xes"
    f.write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    out = resolve_input_path("log.xes", kind="Event log")
    assert out == f.resolve()


def test_relative_path_falls_back_to_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Set up: real file lives under tmp_path/project, but CWD is elsewhere.
    project = tmp_path / "project"
    project.mkdir()
    f = project / "examples" / "log.xes"
    f.parent.mkdir()
    f.write_text("x", encoding="utf-8")

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    # Without the hint, this should fail
    monkeypatch.delenv(ENV_HINT, raising=False)
    with pytest.raises(FileNotFoundError):
        resolve_input_path("examples/log.xes", kind="Event log")

    # With the hint pointing at project, it should resolve
    monkeypatch.setenv(ENV_HINT, str(project))
    out = resolve_input_path("examples/log.xes", kind="Event log")
    assert out == f.resolve()


def test_tilde_expanduser_still_works(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Redirect HOME to tmp_path so ~/log.xes is a controlled file
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
    f = tmp_path / "log.xes"
    f.write_text("x", encoding="utf-8")
    out = resolve_input_path("~/log.xes", kind="Event log")
    assert out == f.resolve()


def test_absolute_path_never_uses_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An absolute path that doesn't exist should NOT fall back to the hint."""
    project = tmp_path / "project"
    project.mkdir()
    decoy = project / "missing.xes"
    decoy.write_text("x", encoding="utf-8")

    monkeypatch.setenv(ENV_HINT, str(project))
    nonexistent_abs = tmp_path / "nowhere" / "missing.xes"
    with pytest.raises(FileNotFoundError):
        resolve_input_path(str(nonexistent_abs), kind="Event log")


def test_error_message_reports_hint_when_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_HINT, str(tmp_path))
    with pytest.raises(FileNotFoundError) as exc:
        resolve_input_path("definitely-missing.xes", kind="OCEL file")
    msg = str(exc.value)
    assert "OCEL file not found" in msg
    assert f"{ENV_HINT}: {tmp_path}" in msg
