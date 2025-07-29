"""Test directory reading functionality in read_file method."""

import tempfile
from pathlib import Path

import pytest

from openhands_aci.editor.editor import OHEditor
from openhands_aci.editor.exceptions import ToolError


def test_read_file_handles_directories():
    """Test that read_file can handle directories without throwing 'Is a directory' error."""

    # Create a temporary directory with some files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create some test files and subdirectories
        (temp_path / 'file1.txt').write_text('Content of file1')
        (temp_path / 'file2.py').write_text("print('hello')")

        subdir = temp_path / 'subdir'
        subdir.mkdir()
        (subdir / 'nested_file.txt').write_text('Nested content')

        # Test reading the directory
        editor = OHEditor()

        # This should not raise "[Errno 21] Is a directory" error
        result = editor.read_file(temp_path)

        # Verify it returns a directory listing
        assert 'Directory listing' in result
        assert str(temp_path) in result
        assert 'file1.txt' in result
        assert 'file2.py' in result
        assert 'subdir/' in result  # Should have trailing slash for directories


def test_read_file_directory_vs_normal_file():
    """Test that read_file behaves differently for directories vs files."""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a file
        test_file = temp_path / 'test.txt'
        test_file.write_text('This is file content')

        editor = OHEditor()

        # Reading the file should return file content
        file_result = editor.read_file(test_file)
        assert file_result == 'This is file content'

        # Reading the directory should return directory listing
        dir_result = editor.read_file(temp_path)
        assert 'Directory listing' in dir_result
        assert 'test.txt' in dir_result


def test_read_file_directory_error_handling():
    """Test error handling when directory operations fail."""

    # Test with a non-existent directory path that would cause find command to fail
    editor = OHEditor()

    # Create a path that doesn't exist
    non_existent = Path('/this/path/does/not/exist')

    # This should raise a ToolError, not the original "Is a directory" error
    with pytest.raises(ToolError) as exc_info:
        editor.read_file(non_existent)

    # Should not be the "Is a directory" error
    assert 'Is a directory' not in str(exc_info.value)


def test_reproduce_original_errno21_issue():
    """Test that reproduces the original [Errno 21] Is a directory issue.

    This test temporarily removes the directory handling to verify the original
    issue would occur, then confirms our fix prevents it.
    """

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a simple directory structure
        (temp_path / 'test_file.txt').write_text('test content')

        editor = OHEditor()

        # With our fix, this should work fine
        result = editor.read_file(temp_path)
        assert 'Directory listing' in result
        assert 'test_file.txt' in result

        # Now let's temporarily patch the method to simulate the old behavior
        original_read_file = editor.read_file

        def old_read_file_behavior(
            path, start_line=None, end_line=None, encoding='utf-8'
        ):
            """Simulate the old behavior that would cause [Errno 21] Is a directory."""
            # Skip directory check - go straight to file operations like the old code
            editor.validate_file(path)
            try:
                with open(path, 'r', encoding=encoding) as f:
                    return ''.join(f)
            except Exception as e:
                raise ToolError(f'Ran into {e} while trying to read {path}') from None

        # Temporarily replace the method
        editor.read_file = old_read_file_behavior

        # Now this should raise the original error
        with pytest.raises(ToolError) as exc_info:
            editor.read_file(temp_path)

        # Verify it's the original "Is a directory" error
        assert 'Is a directory' in str(exc_info.value)
        assert '[Errno 21]' in str(exc_info.value)

        # Restore the original method
        editor.read_file = original_read_file

        # Verify the fix works again
        result = editor.read_file(temp_path)
        assert 'Directory listing' in result
