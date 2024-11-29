import pytest

from openhands_aci.editor.editor import OHEditor
from openhands_aci.editor.exceptions import (
    EditorToolParameterInvalidError,
    EditorToolParameterMissingError,
    ToolError,
)
from openhands_aci.editor.prompts import NAVIGATION_TIPS
from openhands_aci.editor.results import CLIResult, ToolResult


@pytest.fixture
def editor(tmp_path):
    editor = OHEditor()
    # Set up a temporary directory with test files
    test_file = tmp_path / 'test.txt'
    test_file.write_text('This is a test file.\nThis file is for testing purposes.')
    return editor, test_file


@pytest.fixture
def editor_python_file_with_tabs(tmp_path):
    editor = OHEditor()
    # Set up a temporary directory with test files
    test_file = tmp_path / 'test.py'
    test_file.write_text('def test():\n\tprint("Hello, World!")')
    return editor, test_file


def test_view_file(editor):
    editor, test_file = editor
    result = editor(command='view', path=str(test_file))
    assert isinstance(result, CLIResult)
    assert (
        result.output
        == f"""Here's the result of running `cat -n` on {test_file}:
     1\tThis is a test file.
     2\tThis file is for testing purposes.
{NAVIGATION_TIPS}"""
    )


def test_view_directory(editor):
    editor, test_file = editor
    result = editor(command='view', path=str(test_file.parent))
    assert isinstance(result, CLIResult)
    assert str(test_file.parent) in result.output
    assert test_file.name in result.output


def test_create_file(editor):
    editor, test_file = editor
    new_file = test_file.parent / 'new_file.txt'
    result = editor(command='create', path=str(new_file), file_text='New file content')
    assert isinstance(result, ToolResult)
    assert new_file.exists()
    assert new_file.read_text() == 'New file content'
    assert 'File created successfully' in result.output


def test_str_replace_no_linting(editor):
    editor, test_file = editor
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='test file',
        new_str='sample file',
    )
    assert isinstance(result, CLIResult)

    # Test str_replace command
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of {test_file}:
     1\tThis is a sample file.
     2\tThis file is for testing purposes.
Review the changes and make sure they are as expected. Edit the file again if necessary.
{NAVIGATION_TIPS}"""
    )

    # Test that the file content has been updated
    assert 'This is a sample file.' in test_file.read_text()


def test_str_replace_multi_line_no_linting(editor):
    editor, test_file = editor
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='This is a test file.\nThis file is for testing purposes.',
        new_str='This is a sample file.\nThis file is for testing purposes.',
    )
    assert isinstance(result, CLIResult)

    # Test str_replace command
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of {test_file}:
     1\tThis is a sample file.
     2\tThis file is for testing purposes.
Review the changes and make sure they are as expected. Edit the file again if necessary.
{NAVIGATION_TIPS}"""
    )


def test_str_replace_multi_line_with_tabs_no_linting(editor_python_file_with_tabs):
    editor, test_file = editor_python_file_with_tabs
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='def test():\n\tprint("Hello, World!")',
        new_str='def test():\n\tprint("Hello, Universe!")',
    )
    assert isinstance(result, CLIResult)

    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of {test_file}:
     1\tdef test():
     2\t{'\t'.expandtabs()}print("Hello, Universe!")
Review the changes and make sure they are as expected. Edit the file again if necessary.
{NAVIGATION_TIPS}"""
    )


def test_str_replace_with_linting(editor):
    editor, test_file = editor
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='test file',
        new_str='sample file',
        enable_linting=True,
    )
    assert isinstance(result, CLIResult)

    # Test str_replace command
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of {test_file}:
     1\tThis is a sample file.
     2\tThis file is for testing purposes.

No linting issues found in the changes.
Review the changes and make sure they are as expected. Edit the file again if necessary.
{NAVIGATION_TIPS}"""
    )

    # Test that the file content has been updated
    assert 'This is a sample file.' in test_file.read_text()


def test_str_replace_error_multiple_occurrences(editor):
    editor, test_file = editor
    with pytest.raises(ToolError) as exc_info:
        editor(
            command='str_replace', path=str(test_file), old_str='test', new_str='sample'
        )
    assert 'Multiple occurrences of old_str `test`' in str(exc_info.value.message)


def test_str_replace_nonexistent_string(editor):
    editor, test_file = editor
    with pytest.raises(ToolError) as exc_info:
        editor(
            command='str_replace',
            path=str(test_file),
            old_str='Non-existent Line',
            new_str='New Line',
        )
    assert 'No replacement was performed' in str(exc_info)
    assert f'old_str `Non-existent Line` did not appear verbatim in {test_file}' in str(
        exc_info.value.message
    )


def test_insert_no_linting(editor):
    editor, test_file = editor
    result = editor(
        command='insert', path=str(test_file), insert_line=1, new_str='Inserted line'
    )
    assert isinstance(result, CLIResult)
    assert 'Inserted line' in test_file.read_text()
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of the edited file:
     1\tThis is a test file.
     2\tInserted line
     3\tThis file is for testing purposes.
Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary.
{NAVIGATION_TIPS}"""
    )


def test_insert_with_linting(editor):
    editor, test_file = editor
    result = editor(
        command='insert',
        path=str(test_file),
        insert_line=1,
        new_str='Inserted line',
        enable_linting=True,
    )
    assert isinstance(result, CLIResult)
    assert 'Inserted line' in test_file.read_text()
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of the edited file:
     1\tThis is a test file.
     2\tInserted line
     3\tThis file is for testing purposes.

No linting issues found in the changes.
Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary.
{NAVIGATION_TIPS}"""
    )


def test_insert_invalid_line(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(
            command='insert',
            path=str(test_file),
            insert_line=10,
            new_str='Invalid Insert',
        )
    assert 'Invalid `insert_line` parameter' in str(exc_info.value.message)
    assert 'It should be within the range of lines of the file' in str(
        exc_info.value.message
    )


def test_undo_edit(editor):
    editor, test_file = editor
    # Make an edit to be undone
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='test file',
        new_str='sample file',
    )
    # Undo the edit
    result = editor(command='undo_edit', path=str(test_file))
    assert isinstance(result, CLIResult)
    assert 'Last edit to' in result.output
    assert 'test file' in test_file.read_text()  # Original content restored


def test_jump_to_definition(editor, monkeypatch):
    editor, test_file = editor

    # Create a mock git repo with a Python file containing a symbol definition
    test_py_file = test_file.parent / 'test_def.py'
    test_py_file.write_text(
        'class TestSymbol:\n    def test_method(self):\n        pass'
    )

    # Mock GitRepoUtils to simulate a git repo
    class MockGitUtils:
        def get_all_absolute_tracked_files(self, depth=None):
            return [str(test_py_file)]

        def get_absolute_tracked_files_in_directory(
            self, rel_dir_path=None, depth=None
        ):
            return [str(test_py_file)]

    monkeypatch.setattr(
        'openhands_aci.editor.navigator.GitRepoUtils', lambda root: MockGitUtils()
    )

    # Set the root path for SymbolNavigator to the test directory
    import os

    from openhands_aci.editor.navigator import SymbolNavigator

    os.chdir(test_file.parent)
    editor._symbol_navigator = SymbolNavigator()

    # Test basic symbol definition lookup
    result = editor(command='jump_to_definition', path=None, symbol_name='TestSymbol')
    assert isinstance(result, CLIResult)
    assert (
        result.output
        == """
Definition(s) of `TestSymbol`:
test_def.py:
  1│class TestSymbol:
  2│    def test_method(self):
  3│        pass
"""
    )

    # Test symbol not found (fuzzy search)
    result = editor(
        command='jump_to_definition', path=None, symbol_name='NonExistentSymbol'
    )
    assert isinstance(result, CLIResult)
    assert (
        result.output
        == 'No definitions found for `NonExistentSymbol`. Maybe you meant one of these: TestSymbol, test_method?'
    )

    # Test missing symbol_name parameter
    with pytest.raises(EditorToolParameterMissingError) as exc_info:
        editor(command='jump_to_definition', path=None)
    assert 'symbol_name' in str(exc_info.value)


def test_find_references(editor, monkeypatch):
    editor, test_file = editor

    # Create a mock git repo with Python files containing symbol references
    test_def_file = test_file.parent / 'test_def.py'
    test_def_file.write_text(
        'class TestSymbol:\n    def test_method(self):\n        pass'
    )

    test_ref_file = test_file.parent / 'test_ref.py'
    test_ref_file.write_text(
        'from test_def import TestSymbol\n\nobj = TestSymbol()\nobj.test_method()'
    )

    # Mock GitRepoUtils to simulate a git repo
    class MockGitUtils:
        def get_all_absolute_tracked_files(self, depth=None):
            return [str(test_def_file), str(test_ref_file)]

        def get_absolute_tracked_files_in_directory(
            self, rel_dir_path=None, depth=None
        ):
            return [str(test_def_file), str(test_ref_file)]

    monkeypatch.setattr(
        'openhands_aci.editor.navigator.GitRepoUtils', lambda root: MockGitUtils()
    )

    # Set the root path for SymbolNavigator to the test directory
    import os

    from openhands_aci.editor.navigator import SymbolNavigator

    os.chdir(test_file.parent)
    editor._symbol_navigator = SymbolNavigator()

    # Test basic reference lookup
    result = editor(command='find_references', symbol_name='TestSymbol')
    assert isinstance(result, CLIResult)
    assert (
        result.output
        == """
References to `TestSymbol`:
test_ref.py:
...⋮...
  3│obj = TestSymbol()
...⋮...
"""
    )

    # Test symbol not found (fuzzy search)
    result = editor(command='find_references', symbol_name='NonExistentSymbol')
    assert isinstance(result, CLIResult)
    assert (
        result.output
        == 'No references found for `NonExistentSymbol`. Maybe you meant one of these: TestSymbol, test_method?'
    )

    # Test missing symbol_name parameter
    with pytest.raises(EditorToolParameterMissingError) as exc_info:
        editor(command='find_references')
    assert 'symbol_name' in str(exc_info.value)


def test_navigation_no_git_repo(editor, monkeypatch):
    editor, test_file = editor

    # Mock GitRepoUtils to simulate no git repo found
    def mock_git_utils(root):
        raise Exception('No git repository found')

    monkeypatch.setattr('openhands_aci.editor.navigator.GitRepoUtils', mock_git_utils)

    # Test jump_to_definition with no git repo
    result = editor(command='jump_to_definition', path=None, symbol_name='TestSymbol')
    assert isinstance(result, CLIResult)
    assert 'No git repository found' in result.output
    assert 'Navigation commands are disabled' in result.output

    # Test find_references with no git repo
    result = editor(command='find_references', symbol_name='TestSymbol')
    assert isinstance(result, CLIResult)
    assert (
        result.output
        == 'No git repository found. Navigation commands are disabled. Please use bash commands instead.'
    )


def test_validate_path_invalid(editor):
    editor, test_file = editor
    invalid_file = test_file.parent / 'nonexistent.txt'
    with pytest.raises(EditorToolParameterInvalidError):
        editor(command='view', path=str(invalid_file))


def test_create_existing_file_error(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterInvalidError):
        editor(command='create', path=str(test_file), file_text='New content')


def test_str_replace_missing_old_str(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterMissingError):
        editor(command='str_replace', path=str(test_file), new_str='sample')


def test_str_replace_new_str_and_old_str_same(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(
            command='str_replace',
            path=str(test_file),
            old_str='test file',
            new_str='test file',
        )
    assert (
        'No replacement was performed. `new_str` and `old_str` must be different.'
        in str(exc_info.value.message)
    )


def test_insert_missing_line_param(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterMissingError):
        editor(command='insert', path=str(test_file), new_str='Missing insert line')


def test_undo_edit_no_history_error(editor):
    editor, test_file = editor
    empty_file = test_file.parent / 'empty.txt'
    empty_file.write_text('')
    with pytest.raises(ToolError):
        editor(command='undo_edit', path=str(empty_file))
