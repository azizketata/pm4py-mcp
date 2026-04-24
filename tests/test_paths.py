"""Unit tests for pm4py_mcp._paths.resolve_input_path."""

from __future__ import annotations

from pathlib import Path

import pytest

from pm4py_mcp._paths import ENV_HINT, resolve_input_path, resolve_output_path


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


# --- resolve_output_path (0.3.2) ---


def test_resolve_output_absolute_path_returned_as_is(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "out.md"
    out = resolve_output_path(str(target), workspace=tmp_path / "workspace")
    assert out == target


def test_resolve_output_bare_filename_lands_in_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    out = resolve_output_path("just-a-name.xes", workspace=workspace)
    assert out == workspace / "just-a-name.xes"


def test_resolve_output_relative_with_existing_cwd_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If CWD/path parent exists, resolve there (0.3.1 behavior preserved)."""
    (tmp_path / "subdir").mkdir()
    monkeypatch.chdir(tmp_path)
    out = resolve_output_path("subdir/out.xes", workspace=tmp_path / "ws")
    assert out == (tmp_path / "subdir" / "out.xes").resolve()


def test_resolve_output_falls_back_to_hint_when_cwd_parent_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 0.3.2 fix: relative path with subdir uses HINT if CWD parent doesn't exist."""
    project = tmp_path / "project"
    (project / "exports").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setenv(ENV_HINT, str(project))

    out = resolve_output_path("exports/out.xes", workspace=tmp_path / "ws")
    assert out == (project / "exports" / "out.xes").resolve()


def test_resolve_output_falls_back_to_cwd_when_no_parent_anywhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If neither CWD/parent nor HINT/parent exists, fall back to CWD-relative."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(ENV_HINT, raising=False)
    out = resolve_output_path("unknown/out.xes", workspace=tmp_path / "ws")
    assert out == (tmp_path / "unknown" / "out.xes").resolve()
