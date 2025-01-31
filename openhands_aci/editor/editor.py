import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Literal, get_args

from openhands_aci.linter import DefaultLinter
from openhands_aci.utils.shell import run_shell_cmd

from .config import SNIPPET_CONTEXT_WINDOW
from .exceptions import (
    EditorToolParameterInvalidError,
    EditorToolParameterMissingError,
    ToolError,
)
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
        self._file_history: dict[Path, list[Path]] = defaultdict(list)
        self._linter = DefaultLinter()
        self._history_dir = Path(tempfile.gettempdir()) / 'openhands_editor_history'
        self._history_dir.mkdir(exist_ok=True)

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
            # Save initial content to history
            history_path = (
                self._history_dir / f'{_path.name}.{len(self._file_history[_path])}.bak'
            )
            from shutil import copy2

            copy2(_path, history_path)
            self._file_history[_path].append(history_path)
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
        from .file_utils import (
            find_string_in_file,
            get_file_lines,
            replace_string_in_file,
        )

        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ''

        # Find all occurrences of old_str
        line_numbers = find_string_in_file(path, old_str)
        if not line_numbers:
            raise ToolError(
                f'No replacement was performed, old_str `{old_str}` did not appear verbatim in {path}.'
            )
        if len(line_numbers) > 1:
            raise ToolError(
                f'No replacement was performed. Multiple occurrences of old_str `{old_str}` in lines {line_numbers}. Please ensure it is unique.'
            )

        # Perform the replacement first to avoid unnecessary copying
        if not replace_string_in_file(path, old_str, new_str):
            raise ToolError(
                f'No replacement was performed, old_str `{old_str}` did not appear verbatim in {path}.'
            )

        # Save current content to history
        history_path = (
            self._history_dir / f'{path.name}.{len(self._file_history[path])}.bak'
        )
        from shutil import copy2

        copy2(path, history_path)
        self._file_history[path].append(history_path)

        # Create a snippet of the edited section
        replacement_line = line_numbers[0]
        start_line = max(1, replacement_line - SNIPPET_CONTEXT_WINDOW)
        end_line = replacement_line + SNIPPET_CONTEXT_WINDOW + new_str.count('\n')

        snippet_lines = []
        for line_num, line in get_file_lines(path, start_line, end_line):
            snippet_lines.append(line)
        snippet = '\n'.join(snippet_lines)

        # Prepare the success message
        success_message = f'The file {path} has been edited. '
        success_message += self._make_output(
            snippet, f'a snippet of {path}', start_line
        )

        if enable_linting:
            # Run linting on the changes
            old_content = self._file_history[path][-1].read_text()
            new_content = self.read_file(path)
            lint_results = self._run_linting(old_content, new_content, path)
            success_message += '\n' + lint_results + '\n'

        success_message += 'Review the changes and make sure they are as expected. Edit the file again if necessary.'
        return CLIResult(
            output=success_message,
            prev_exist=True,
            path=str(path),
            old_content=self._file_history[path][-1].read_text(),
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

        from .file_utils import get_file_lines

        # Get total number of lines efficiently
        num_lines = 0
        with open(path, 'rb') as f:
            num_lines = sum(1 for _ in f)

        if not view_range:
            # Read all lines in chunks
            def read_chunks():
                chunk_lines = []
                chunk_size = 0
                for line_num, line in get_file_lines(path):
                    chunk_lines.append(line)
                    chunk_size += len(line) + 1  # +1 for newline
                    if chunk_size >= 1024 * 1024:  # 1MB chunks
                        yield '\n'.join(chunk_lines)
                        chunk_lines = []
                        chunk_size = 0
                if chunk_lines:
                    yield '\n'.join(chunk_lines)

            return CLIResult(
                output=self._make_output(list(read_chunks()), str(path), 1),
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

        # Read requested lines in chunks
        if end_line == -1:
            end_line = num_lines

        def read_range_chunks():
            chunk_lines = []
            chunk_size = 0
            for line_num, line in get_file_lines(path, start_line, end_line):
                chunk_lines.append(line)
                chunk_size += len(line) + 1  # +1 for newline
                if chunk_size >= 1024 * 1024:  # 1MB chunks
                    yield '\n'.join(chunk_lines)
                    chunk_lines = []
                    chunk_size = 0
            if chunk_lines:
                yield '\n'.join(chunk_lines)

        return CLIResult(
            path=str(path),
            output=self._make_output(list(read_range_chunks()), str(path), start_line),
            prev_exist=True,
        )

    def write_file(self, path: Path, file_text: str) -> None:
        """
        Write the content of a file to a given path; raise a ToolError if an error occurs.
        """
        try:
            with open(path, 'w') as f:
                f.write(file_text)
        except Exception as e:
            raise ToolError(f'Ran into {e} while trying to write to {path}') from None

    def insert(
        self, path: Path, insert_line: int, new_str: str, enable_linting: bool
    ) -> CLIResult:
        """
        Implement the insert command, which inserts new_str at the specified line in the file content.
        """
        from .file_utils import get_file_lines

        # Get total number of lines first
        num_lines = sum(1 for _ in get_file_lines(path))

        if insert_line < 0 or insert_line > num_lines:
            raise EditorToolParameterInvalidError(
                'insert_line',
                insert_line,
                f'It should be within the range of lines of the file: {[0, num_lines]}',
            )

        # Create temporary file for the insertion
        temp_path = path.with_suffix(path.suffix + '.tmp')
        try:
            with open(temp_path, 'w') as out:
                current_line = 1
                # Write lines before insertion point
                for line_num, line in get_file_lines(path, end_line=insert_line):
                    out.write(line.expandtabs() + '\n')
                    current_line += 1

                # Write the new content
                for line in new_str.expandtabs().split('\n'):
                    out.write(line + '\n')

                # Write remaining lines
                for line_num, line in get_file_lines(path, start_line=insert_line + 1):
                    out.write(line.expandtabs() + '\n')

            # Replace original file
            temp_path.replace(path)

            # Save current content to history
            history_path = (
                self._history_dir / f'{path.name}.{len(self._file_history[path])}.bak'
            )
            from shutil import copy2

            copy2(path, history_path)
            self._file_history[path].append(history_path)

            # Create snippet for display
            snippet_lines = []
            start_line = max(1, insert_line - SNIPPET_CONTEXT_WINDOW)
            end_line = insert_line + SNIPPET_CONTEXT_WINDOW + len(new_str.split('\n'))

            for line_num, line in get_file_lines(path, start_line, end_line):
                snippet_lines.append(line)
            snippet = '\n'.join(snippet_lines)

            success_message = f'The file {path} has been edited. '
            success_message += self._make_output(
                snippet,
                'a snippet of the edited file',
                start_line,
            )

        finally:
            if temp_path.exists():
                temp_path.unlink()

        if enable_linting:
            # Run linting on the changes
            old_content = self._file_history[path][-1].read_text()
            new_content = self.read_file(path)
            lint_results = self._run_linting(old_content, new_content, path)
            success_message += '\n' + lint_results + '\n'

        success_message += 'Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary.'
        return CLIResult(
            output=success_message,
            prev_exist=True,
            path=str(path),
            old_content=self._file_history[path][-1].read_text(),
            new_content=self.read_file(path),
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
        if not self._file_history[path]:
            raise ToolError(f'No edit history found for {path}.')

        current_text = self.read_file(path).expandtabs()
        history_path = self._file_history[path].pop()
        old_text = history_path.read_text().expandtabs()
        self.write_file(path, old_text)
        history_path.unlink()

        return CLIResult(
            output=f'Last edit to {path} undone successfully. {self._make_output(old_text, str(path))}',
            path=str(path),
            prev_exist=True,
            old_content=current_text,
            new_content=old_text,
        )

    def read_file(self, path: Path) -> str:
        """
        Read the content of a file from a given path; raise a ToolError if an error occurs.
        """
        try:
            with open(path, 'r') as f:
                return f.read()
        except Exception as e:
            raise ToolError(f'Ran into {e} while trying to read {path}') from None

    def _make_output(
        self,
        snippet_content: str | list[str],
        snippet_description: str,
        start_line: int = 1,
        expand_tabs: bool = True,
    ) -> str:
        """
        Generate output for the CLI based on the content of a code snippet.
        """
        if isinstance(snippet_content, str):
            snippet_content = [snippet_content]

        def process_chunks():
            current_line = start_line
            for chunk in snippet_content:
                chunk = maybe_truncate(
                    chunk, truncate_notice=FILE_CONTENT_TRUNCATED_NOTICE
                )
                if expand_tabs:
                    chunk = chunk.expandtabs()

                for line in chunk.split('\n'):
                    yield f'{current_line:6}\t{line}'
                    current_line += 1

        return (
            f"Here's the result of running `cat -n` on {snippet_description}:\n"
            + '\n'.join(process_chunks())
            + '\n'
        )

    def _run_linting(self, old_content: str, new_content: str, path: Path) -> str:
        """
        Run linting on file changes and return formatted results.
        """
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create paths with exact filenames in temp directory
            temp_old = Path(temp_dir) / f'old.{path.name}'
            temp_new = Path(temp_dir) / f'new.{path.name}'

            # Write content to temporary files in chunks
            with open(temp_old, 'w') as f:
                f.write(old_content)
            with open(temp_new, 'w') as f:
                f.write(new_content)

            # Run linting on the changes
            results = self._linter.lint_file_diff(str(temp_old), str(temp_new))

            if not results:
                return 'No linting issues found in the changes.'

            # Format results
            output = ['Linting issues found in the changes:']
            for result in results:
                output.append(
                    f'- Line {result.line}, Column {result.column}: {result.message}'
                )
            return '\n'.join(output) + '\n'
