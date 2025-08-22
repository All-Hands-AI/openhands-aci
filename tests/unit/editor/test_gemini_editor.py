from pathlib import Path

import pytest

from openhands_aci.editor.gemini_editor import GeminiEditor
from openhands_aci.editor.exceptions import EditorToolParameterInvalidError, ToolError


def write_text(path: Path, content: str, eol='\n'):
    # Normalize to requested eol when writing for test setup
    content = content.replace('\n', eol)
    path.write_text(content)


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def test_replace_single_occurrence(tmp_path):
    p = tmp_path / 'a.txt'
    p.write_text('hello\nworld\n')
    ed = GeminiEditor(workspace_root=str(tmp_path))
    res = ed(command='replace', path=str(p), old_str='world', new_str='there')
    assert res.error is None
    assert res.prev_exist is True
    assert res.old_content == 'hello\nworld\n'
    assert res.new_content == 'hello\nthere\n'


def test_replace_mismatch_expected_count(tmp_path):
    p = tmp_path / 'b.txt'
    p.write_text('x x x\n')
    ed = GeminiEditor(workspace_root=str(tmp_path))
    res = ed(command='replace', path=str(p), old_str='x', new_str='y', expected_replacements=2)
    assert res.error is not None
    assert 'expected 2 occurrences but found 3' in res.error.lower()


def test_replace_zero_occurrence_error(tmp_path):
    p = tmp_path / 'c.txt'
    p.write_text('abc\n')
    ed = GeminiEditor(workspace_root=str(tmp_path))
    res = ed(command='replace', path=str(p), old_str='zzz', new_str='mmm')
    assert res.error is not None
    assert '0 occurrences found' in res.error.lower()


def test_replace_old_equals_new_error(tmp_path):
    p = tmp_path / 'd.txt'
    p.write_text('same\n')
    ed = GeminiEditor(workspace_root=str(tmp_path))
    res = ed(command='replace', path=str(p), old_str='same', new_str='same')
    assert res.error is not None
    assert 'new_string must be different from old_string' in res.error.lower()


def test_replace_create_when_missing_and_old_empty(tmp_path):
    p = tmp_path / 'new.txt'
    ed = GeminiEditor(workspace_root=str(tmp_path))
    assert not p.exists()
    res = ed(command='replace', path=str(p), old_str='', new_str='content')
    assert res.error is None
    assert p.exists()
    assert p.read_text() == 'content'


def test_replace_missing_file_and_old_not_empty_error(tmp_path):
    p = tmp_path / 'missing.txt'
    ed = GeminiEditor(workspace_root=str(tmp_path))
    res = ed(command='replace', path=str(p), old_str='x', new_str='y')
    assert res.error is not None
    assert 'file does not exist' in res.error.lower()


def test_crlf_normalization_and_preservation(tmp_path):
    p = tmp_path / 'crlf.txt'
    # Write with CRLF
    write_text(p, 'A\nB\nC\n', eol='\r\n')
    data_before = read_bytes(p)
    ed = GeminiEditor(workspace_root=str(tmp_path))
    res = ed(command='replace', path=str(p), old_str='B', new_str='X')
    assert res.error is None
    data_after = read_bytes(p)
    # File should still contain CRLFs and same number of bytes change as expected
    assert b'\r\n' in data_after
    assert data_before != data_after


def test_enforce_workspace_boundary(tmp_path):
    outside = Path('/tmp/outside.txt')
    ed = GeminiEditor(workspace_root=str(tmp_path))
    res = ed(command='replace', path=str(outside), old_str='', new_str='x')
    assert res.error is not None
    assert 'workspace root' in res.error.lower()


def test_directory_path_rejected(tmp_path):
    ed = GeminiEditor(workspace_root=str(tmp_path))
    res = ed(command='replace', path=str(tmp_path), old_str='a', new_str='b')
    assert res.error is not None
    assert 'is a directory' in res.error.lower()
