import shutil
import tempfile
from pathlib import Path
from typing import Literal, Optional, get_args

from openhands_aci.linter import DefaultLinter
from openhands_aci.utils.shell import run_shell_cmd

from .config import SNIPPET_CONTEXT_WINDOW
from .exceptions import (
    EditorToolParameterInvalidError,
    EditorToolParameterMissingError,
    ToolError,
)
from .file_ops import (
    FileError,
    FileTooLargeError,
    InvalidFileTypeError,
    read_file_range,
    replace_in_file,
)
from .history import FileHistoryManager
from .prompts import DIRECTORY_CONTENT_TRUNCATED_NOTICE, FILE_CONTENT_TRUNCATED_NOTICE
from .results import CLIResult, maybe_truncate


Command = Literal[
    'view',
    'create',
    'str_replace',
    'insert',
    'undo_edit',
    # 'jump_to_definition', TODO:
    # 'find_references' TODO:
]


class OHEditor:
    """
    An filesystem editor tool that allows the agent to
    - view
    - create
    - navigate
    - edit files
    The tool parameters are defined by Anthropic and are not editable.

    Original implementation: https://github.com/anthropics/anthropic-quickstarts/blob/main/computer-use-demo/computer_use_demo/tools/edit.py
    """

    TOOL_NAME = 'oh_editor'

    def __init__(self):
        self._linter = DefaultLinter()
        self._history_manager = FileHistoryManager(max_history_per_file=10)

    def __call__(
        self,
        *,
        command: Command,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        enable_linting: bool = False,
        **kwargs,
    ) -> CLIResult:
        _path = Path(path)
        self.validate_path(command, _path)
        if command == 'view':
            return self.view(_path, view_range)
        elif command == 'create':
            if file_text is None:
                raise EditorToolParameterMissingError(command, 'file_text')
            self.write_file(_path, file_text)
            self._history_manager.add_history(_path, file_text)
            return CLIResult(
                path=str(_path),
                new_content=file_text,
                prev_exist=False,
                output=f'File created successfully at: {_path}',
            )
        elif command == 'str_replace':
            if old_str is None:
                raise EditorToolParameterMissingError(command, 'old_str')
            if new_str == old_str:
                raise EditorToolParameterInvalidError(
                    'new_str',
                    new_str,
                    'No replacement was performed. `new_str` and `old_str` must be different.',
                )
            return self.str_replace(_path, old_str, new_str, enable_linting)
        elif command == 'insert':
            if insert_line is None:
                raise EditorToolParameterMissingError(command, 'insert_line')
            if new_str is None:
                raise EditorToolParameterMissingError(command, 'new_str')
            return self.insert(_path, insert_line, new_str, enable_linting)
        elif command == 'undo_edit':
            return self.undo_edit(_path)

        raise ToolError(
            f'Unrecognized command {command}. The allowed commands for the {self.TOOL_NAME} tool are: {", ".join(get_args(Command))}'
        )

    def str_replace(
        self, path: Path, old_str: str, new_str: str | None, enable_linting: bool
    ) -> CLIResult:
        """
        Implement the str_replace command, which replaces old_str with new_str in the file content.
        """
        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ''

        try:
            # Use the efficient replace_in_file function
            result = replace_in_file(path, old_str, new_str)
            if result is None:
                raise ToolError(
                    f'No replacement was performed, old_str `{old_str}` did not appear verbatim in {path}.'
                )
            
            replacement_line, matched_text = result
            
            # Save the content to history
            file_content = self.read_file(path)
            self._history_manager.add_history(path, file_content)
            
            # Create a snippet of the edited section
            start_line = max(0, replacement_line - SNIPPET_CONTEXT_WINDOW)
            end_line = replacement_line + SNIPPET_CONTEXT_WINDOW + new_str.count('\n')
            
            # Read just the snippet range
            snippet = self.read_file(path, start_line=start_line, end_line=end_line)
            
        except FileError as e:
            raise ToolError(str(e)) from None
        except ValueError as e:
            # Convert the error message to match the original format
            msg = str(e)
            if 'Multiple occurrences found in lines' in msg:
                line_numbers = msg[msg.find('['):msg.find(']')+1]
                raise ToolError(
                    f'No replacement was performed. Multiple occurrences of old_str `{old_str}` in lines {line_numbers}. Please ensure it is unique.'
                ) from None
            raise ToolError(str(e)) from None

        # Prepare the success message
        success_message = f'The file {path} has been edited. '
        success_message += self._make_output(
            snippet, f'a snippet of {path}', start_line + 1
        )

        if enable_linting:
            # Run linting on the changes
            lint_results = self._run_linting(file_content, self.read_file(path), path)
            success_message += '\n' + lint_results + '\n'

        success_message += 'Review the changes and make sure they are as expected. Edit the file again if necessary.'
        return CLIResult(
            output=success_message,
            prev_exist=True,
            path=str(path),
            old_content=file_content,
            new_content=self.read_file(path),
        )

    def view(self, path: Path, view_range: list[int] | None = None) -> CLIResult:
        """
        View the contents of a file or a directory.
        """
        if path.is_dir():
            if view_range:
                raise EditorToolParameterInvalidError(
                    'view_range',
                    view_range,
                    'The `view_range` parameter is not allowed when `path` points to a directory.',
                )

            # First count hidden files/dirs in current directory only
            # -mindepth 1 excludes . and .. automatically
            _, hidden_stdout, _ = run_shell_cmd(
                rf"find -L {path} -mindepth 1 -maxdepth 1 -name '.*'"
            )
            hidden_count = (
                len(hidden_stdout.strip().split('\n')) if hidden_stdout.strip() else 0
            )

            # Then get files/dirs up to 2 levels deep, excluding hidden entries at both depth 1 and 2
            _, stdout, stderr = run_shell_cmd(
                rf"find -L {path} -maxdepth 2 -not \( -path '{path}/\.*' -o -path '{path}/*/\.*' \) | sort",
                truncate_notice=DIRECTORY_CONTENT_TRUNCATED_NOTICE,
            )
            if not stderr:
                # Add trailing slashes to directories
                paths = stdout.strip().split('\n') if stdout.strip() else []
                formatted_paths = []
                for p in paths:
                    if Path(p).is_dir():
                        formatted_paths.append(f'{p}/')
                    else:
                        formatted_paths.append(p)

                msg = [
                    f"Here's the files and directories up to 2 levels deep in {path}, excluding hidden items:\n"
                    + '\n'.join(formatted_paths)
                ]
                if hidden_count > 0:
                    msg.append(
                        f"\n{hidden_count} hidden files/directories in this directory are excluded. You can use 'ls -la {path}' to see them."
                    )
                stdout = '\n'.join(msg)
            return CLIResult(
                output=stdout,
                error=stderr,
                path=str(path),
                prev_exist=True,
            )

        # Get number of lines in file
        num_lines = sum(1 for _ in open(path))

        start_line = 1
        if not view_range:
            file_content = self.read_file(path)
            return CLIResult(
                output=self._make_output(file_content, str(path), start_line),
                path=str(path),
                prev_exist=True,
            )

        if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
            raise EditorToolParameterInvalidError(
                'view_range',
                view_range,
                'It should be a list of two integers.',
            )

        start_line, end_line = view_range
        if start_line < 1 or start_line > num_lines:
            raise EditorToolParameterInvalidError(
                'view_range',
                view_range,
                f'Its first element `{start_line}` should be within the range of lines of the file: {[1, num_lines]}.',
            )

        if end_line > num_lines:
            raise EditorToolParameterInvalidError(
                'view_range',
                view_range,
                f'Its second element `{end_line}` should be smaller than the number of lines in the file: `{num_lines}`.',
            )

        if end_line != -1 and end_line < start_line:
            raise EditorToolParameterInvalidError(
                'view_range',
                view_range,
                f'Its second element `{end_line}` should be greater than or equal to the first element `{start_line}`.',
            )

        if end_line == -1:
            end_line = num_lines

        file_content = self.read_file(path, start_line=start_line, end_line=end_line)
        return CLIResult(
            path=str(path),
            output=self._make_output(file_content, str(path), start_line),
            prev_exist=True,
        )

    def write_file(self, path: Path, file_text: str) -> None:
        """
        Write the content of a file to a given path; raise a ToolError if an error occurs.
        """
        try:
            path.write_text(file_text)
        except Exception as e:
            raise ToolError(f'Ran into {e} while trying to write to {path}') from None

    def insert(
        self, path: Path, insert_line: int, new_str: str, enable_linting: bool
    ) -> CLIResult:
        """
        Implement the insert command, which inserts new_str at the specified line in the file content.
        """
        # Count lines in file
        num_lines = sum(1 for _ in open(path))

        if insert_line < 0 or insert_line > num_lines:
            raise EditorToolParameterInvalidError(
                'insert_line',
                insert_line,
                f'It should be within the range of lines of the file: {[0, num_lines]}',
            )

        new_str = new_str.expandtabs()
        new_str_lines = new_str.split('\n')

        # Create temporary file for the new content
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            # Copy lines before insert point
            with open(path, 'r') as f:
                for i, line in enumerate(f, 1):
                    if i > insert_line:
                        break
                    temp_file.write(line.expandtabs())

            # Insert new content
            for line in new_str_lines:
                temp_file.write(line + '\n')

            # Copy remaining lines
            with open(path, 'r') as f:
                for i, line in enumerate(f, 1):
                    if i <= insert_line:
                        continue
                    temp_file.write(line.expandtabs())

        # Read the original content for history
        file_text = self.read_file(path)

        # Move temporary file to original location
        shutil.move(temp_file.name, path)

        # Read just the snippet range
        start_line = max(1, insert_line - SNIPPET_CONTEXT_WINDOW)
        end_line = min(
            num_lines + len(new_str_lines),
            insert_line + SNIPPET_CONTEXT_WINDOW + len(new_str_lines),
        )
        snippet = self.read_file(path, start_line=start_line, end_line=end_line)

        # Save history
        self._history_manager.add_history(path, file_text)

        # Read new content for result
        new_file_text = self.read_file(path)

        success_message = f'The file {path} has been edited. '
        success_message += self._make_output(
            snippet,
            'a snippet of the edited file',
            max(1, insert_line - SNIPPET_CONTEXT_WINDOW + 1),
        )

        if enable_linting:
            # Run linting on the changes
            lint_results = self._run_linting(file_text, new_file_text, path)
            success_message += '\n' + lint_results + '\n'

        success_message += 'Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary.'
        return CLIResult(
            output=success_message,
            prev_exist=True,
            path=str(path),
            old_content=file_text,
            new_content=new_file_text,
        )

    def validate_path(self, command: Command, path: Path) -> None:
        """
        Check that the path/command combination is valid.
        """
        # Check if its an absolute path
        if not path.is_absolute():
            suggested_path = Path.cwd() / path
            raise EditorToolParameterInvalidError(
                'path',
                path,
                f'The path should be an absolute path, starting with `/`. Maybe you meant {suggested_path}?',
            )
        # Check if path and command are compatible
        if command == 'create' and path.exists():
            raise EditorToolParameterInvalidError(
                'path',
                path,
                f'File already exists at: {path}. Cannot overwrite files using command `create`.',
            )
        if command != 'create' and not path.exists():
            raise EditorToolParameterInvalidError(
                'path',
                path,
                f'The path {path} does not exist. Please provide a valid path.',
            )
        if command != 'view' and path.is_dir():
            raise EditorToolParameterInvalidError(
                'path',
                path,
                f'The path {path} is a directory and only the `view` command can be used on directories.',
            )

    def undo_edit(self, path: Path) -> CLIResult:
        """
        Implement the undo_edit command.
        """
        current_text = self.read_file(path).expandtabs()
        old_text = self._history_manager.get_last_history(path)
        if old_text is None:
            raise ToolError(f'No edit history found for {path}.')

        self.write_file(path, old_text)

        return CLIResult(
            output=f'Last edit to {path} undone successfully. {self._make_output(old_text, str(path))}',
            path=str(path),
            prev_exist=True,
            old_content=current_text,
            new_content=old_text,
        )

    def read_file(
        self,
        path: Path,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        """
        Read the content of a file from a given path; raise a ToolError if an error occurs.

        Args:
            path: Path to the file to read
            start_line: Optional start line number (1-based). If provided with end_line, only reads that range.
            end_line: Optional end line number (1-based). Must be provided with start_line.
        """
        try:
            return read_file_range(path, start_line, end_line)
        except FileError as e:
            raise ToolError(str(e)) from None
        except Exception as e:
            raise ToolError(f'Ran into {e} while trying to read {path}') from None

    def _make_output(
        self,
        snippet_content: str,
        description: str,
        start_line: int = 1,
    ) -> str:
        """
        Format the output of a command with line numbers and a description.
        """
        return f"Here's the result of running `cat -n` on {description}:\n{maybe_truncate(snippet_content, start_line, FILE_CONTENT_TRUNCATED_NOTICE)}"

    def _run_linting(self, old_content: str, new_content: str, path: Path) -> str:
        """
        Run linting on the changes.
        """
        return self._linter.lint_changes(old_content, new_content, path)