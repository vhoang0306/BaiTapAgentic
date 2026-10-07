"""File tools: đọc/ghi đúng phạm vi, lỗi có cấu trúc, chặn traversal/absolute/symlink escape."""

import json

import pytest

import paths
from reset_workspace import WorkspaceError, ensure_workspace, reset_workspace
from tools import list_files, read_file, write_file
from tools.files import MAX_READ_BYTES, _list_files, _read, _write


@pytest.fixture
def ws(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "data").mkdir(parents=True)
    (workspace / "output").mkdir()
    (workspace / "data" / "note.md").write_text("Xin chào", encoding="utf-8")
    return workspace


def test_read_ok(ws):
    assert _read(ws, "data/note.md") == {"ok": True, "path": "data/note.md", "content": "Xin chào"}


def test_read_missing_file(ws):
    result = _read(ws, "data/khong-ton-tai.md")
    assert result["ok"] is False and result["error"]["code"] == "FILE_NOT_FOUND"


@pytest.mark.parametrize("path", ["../secret.txt", "data/../../secret.txt"])
def test_read_traversal_blocked(ws, path):
    (ws.parent / "secret.txt").write_text("secret")
    assert _read(ws, path)["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_read_absolute_path_blocked(ws):
    assert _read(ws, str(ws / "data" / "note.md"))["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_read_symlink_escape_blocked(ws):
    (ws.parent / "secret.txt").write_text("secret")
    try:
        (ws / "data" / "link.txt").symlink_to(ws.parent / "secret.txt")
    except OSError as exc:
        pytest.skip(f"Symlink creation unavailable: {exc}")
    result = _read(ws, "data/link.txt")
    assert result["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"
    assert "content" not in result


def test_list_files_returns_sorted_direct_entries(ws):
    (ws / "data" / "z.md").write_text("z", encoding="utf-8")
    (ws / "data" / "a-dir").mkdir()
    result = _list_files(ws, "data")
    assert result == {
        "ok": True,
        "path": "data",
        "entries": [
            {"name": "a-dir", "path": "data/a-dir", "type": "directory"},
            {"name": "note.md", "path": "data/note.md", "type": "file"},
            {"name": "z.md", "path": "data/z.md", "type": "file"},
        ],
    }


@pytest.mark.parametrize(
    ("path", "expected_code"),
    [
        ("missing", "DIRECTORY_NOT_FOUND"),
        ("data/note.md", "NOT_A_DIRECTORY"),
        ("../secret", "PATH_OUTSIDE_WORKSPACE"),
    ],
)
def test_list_files_rejects_invalid_paths(ws, path, expected_code):
    assert _list_files(ws, path)["error"]["code"] == expected_code


def test_list_files_rejects_absolute_path(ws):
    assert _list_files(ws, str(ws / "data"))["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_list_files_rejects_symlink_escape(ws, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private.txt").write_text("private", encoding="utf-8")
    try:
        (ws / "escape").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlink creation unavailable: {exc}")
    assert _list_files(ws, "escape")["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_read_too_large_and_non_utf8(ws):
    (ws / "data" / "big.txt").write_text("a" * (MAX_READ_BYTES + 1))
    (ws / "data" / "bin.dat").write_bytes(b"\xff\xfe\x00")
    assert _read(ws, "data/big.txt")["error"]["code"] == "FILE_TOO_LARGE"
    assert _read(ws, "data/bin.dat")["error"]["code"] == "NOT_UTF8_TEXT"
    assert _read(ws, "data")["error"]["code"] == "IS_A_DIRECTORY"


def test_write_created_then_updated(ws):
    first = _write(ws, "output/reports/summary.md", "# Tóm tắt")
    assert first == {"ok": True, "path": "output/reports/summary.md", "bytes": len("# Tóm tắt".encode()), "status": "created"}
    second = _write(ws, "output/reports/summary.md", "v2")
    assert second["status"] == "updated" and second["bytes"] == 2
    assert (ws / "output" / "reports" / "summary.md").read_text(encoding="utf-8") == "v2"


@pytest.mark.parametrize("path", ["data/note.md", "summary.md", "output", "output/../data/x.md", "../output/x.md"])
def test_write_outside_output_rejected(ws, path):
    result = _write(ws, path, "x")
    assert result["ok"] is False
    assert result["error"]["code"] in {"PATH_OUTSIDE_OUTPUT", "PATH_OUTSIDE_WORKSPACE"}
    assert (ws / "data" / "note.md").read_text(encoding="utf-8") == "Xin chào"


def test_write_absolute_and_symlink_escape_rejected(ws, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (ws / "output" / "escape").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlink creation unavailable: {exc}")
    assert _write(ws, str(ws / "output" / "a.md"), "x")["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"
    assert _write(ws, "output/escape/a.md", "x")["ok"] is False
    assert list(outside.iterdir()) == []


def test_tools_return_json_against_project_workspace(lab_dirs):
    listing = json.loads(list_files.invoke({"path": "data"}))
    assert listing["ok"] is True
    assert any(entry["name"] == "weekly_notes.md" for entry in listing["entries"])
    policies = json.loads(list_files.invoke({"path": "data/policies"}))
    assert [entry["name"] for entry in policies["entries"]] == ["policy-before-oct.md", "policy-from-oct.md"]
    assert json.loads(read_file.invoke({"path": "data/weekly_notes.md"}))["ok"] is True
    written = json.loads(write_file.invoke({"path": "output/t.md", "content": "ok"}))
    assert written["status"] == "created"
    assert json.loads(read_file.invoke({"path": "output/t.md"}))["content"] == "ok"


def test_registered_list_files_returns_errors_for_invalid_paths(lab_dirs):
    invalid_paths = [
        ("data/weekly_notes.md", "NOT_A_DIRECTORY"),
        ("data/missing", "DIRECTORY_NOT_FOUND"),
        ("../outside", "PATH_OUTSIDE_WORKSPACE"),
        (str(paths.WORKSPACE_DIR), "PATH_OUTSIDE_WORKSPACE"),
    ]
    for path, expected_code in invalid_paths:
        result = json.loads(list_files.invoke({"path": path}))
        assert result["ok"] is False
        assert result["error"]["code"] == expected_code


def test_policy_files_are_discovered_after_rename(lab_dirs):
    policy_dir = paths.WORKSPACE_DIR / "data" / "policies"
    renamed_paths = []
    for index, source in enumerate(sorted(policy_dir.glob("*.md"))):
        renamed = policy_dir / f"renamed-{index}.md"
        source.rename(renamed)
        renamed_paths.append(renamed)

    listing = json.loads(list_files.invoke({"path": "data/policies"}))
    assert [entry["name"] for entry in listing["entries"]] == ["renamed-0.md", "renamed-1.md"]
    contents = [json.loads(read_file.invoke({"path": f"data/policies/{path.name}"}))["content"] for path in renamed_paths]
    assert any("Áp dụng cho ngày mua trước 2026-10-01." in content for content in contents)
    assert any("Áp dụng cho ngày mua từ 2026-10-01" in content for content in contents)


def test_reset_restores_fixtures_and_requires_marker(tmp_path):
    fixtures = tmp_path / "fixtures"
    (fixtures / "data").mkdir(parents=True)
    (fixtures / "data" / "a.md").write_text("A")
    workspace = tmp_path / "workspace"
    ensure_workspace(workspace, fixtures)
    (workspace / "data" / "a.md").write_text("changed")
    (workspace / "output" / "r.md").write_text("R")
    ensure_workspace(workspace, fixtures)  # không ghi đè khi đã có workspace
    assert (workspace / "data" / "a.md").read_text() == "changed"
    reset_workspace(workspace, fixtures)
    assert (workspace / "data" / "a.md").read_text() == "A"
    assert list((workspace / "output").iterdir()) == []

    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("keep")
    with pytest.raises(WorkspaceError):
        reset_workspace(foreign, fixtures)
    with pytest.raises(WorkspaceError):
        ensure_workspace(foreign, fixtures)
    assert (foreign / "keep.txt").read_text() == "keep"
