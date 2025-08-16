from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .editor import OHEditor
from .exceptions import EditorToolParameterInvalidError, EditorToolParameterMissingError, ToolError
from .results import CLIResult


@dataclass
class ReplaceResult:
    count: int
    prev_exist: bool
    old_content: str
    new_content: str


class GeminiEditor(OHEditor):
    """
    Gemini-CLI–compatible editor subset for filesystem operations used by Gemini models.

    Currently implements only the `replace` command with behavior aligned to Gemini CLI:
    - Literal replacement with CRLF -> LF normalization when matching
    - Error if old_string == new_string
    - If old_string == '' and file does not exist: create file with new_string
    - If file does not exist and old_string != '': error
    - expected_replacements default = 1; enforce exact match count; error on 0 or mismatch
    """

    TOOL_NAME = 'gemini_editor'

    def __call__(
        self,
        *,
        command: str,
        path: str,
        old_str: str | None = None,
        new_str: str | None = None,
        expected_replacements: int | None = None,
        **_: object,
    ) -> CLIResult:
        _path = Path(path)
        if not _path.is_absolute():
            raise EditorToolParameterInvalidError(
                'path', path, 'The path should be an absolute path, starting with `/`.'
            )
        # Enforce workspace boundary if configured
        if getattr(self, '_cwd', None) is not None:
            try:
                if not _path.resolve().is_relative_to(self._cwd):  # type: ignore[arg-type]
                    raise EditorToolParameterInvalidError(
                        'path', path, f'Path must be inside the workspace root: {self._cwd}'
                    )
            except Exception:
                # Fallback: basic prefix check if resolve/is_relative_to not available
                if not str(_path.resolve()).startswith(str(self._cwd)):
                    raise EditorToolParameterInvalidError(
                        'path', path, f'Path must be inside the workspace root: {self._cwd}'
                    )
        if command != 'replace':
            raise ToolError(
                f'Unrecognized command {command}. The allowed command for the {self.TOOL_NAME} tool is: replace.'
            )
        if new_str is None:
            raise EditorToolParameterMissingError('replace', 'new_string')
        if old_str is None:
            old_str = ''
        # Disallow directories
        if _path.is_dir():
            raise EditorToolParameterInvalidError(
                'path', path, f'The path {path} is a directory and only the `view` command can be used on directories.'
            )

        return self._replace(_path, old_str, new_str, expected_replacements)

    def _replace(
        self,
        path: Path,
        old: str,
        new: str,
        expected: int | None,
    ) -> CLIResult:
        if new == old:
            raise EditorToolParameterInvalidError(
                'new_string', new, 'No replacement performed: new_string and old_string are identical.'
            )

        # File existence handling
        if not path.exists():
            if old == '':
                # Create new file with new_string content
                self.write_file(path, new)
                self._history_manager.add_history(path, '')
                return CLIResult(
                    output=f'File created successfully at: {path}',
                    path=str(path),
                    prev_exist=False,
                    old_content='',
                    new_content=new,
                )
            else:
                raise ToolError(f'The path {path} does not exist. Please provide a valid path.')

        # Read raw content and normalize only for matching
        raw_text = self.read_file(path)
        normalized_text = raw_text.replace('\r\n', '\n').replace('\r', '\n')

        if old == '':
            # Creating into existing file is ambiguous; align to error
            raise EditorToolParameterInvalidError(
                'old_string', old, 'old_string cannot be empty when the file already exists.'
            )

        count = normalized_text.count(old)
        if expected is None:
            expected = 1

        if count == 0:
            raise ToolError(
                f'No replacement was performed; old_string did not appear in {path}.'
            )
        if count != expected:
            raise ToolError(
                f'Expected {expected} replacements, but found {count} occurrences. Please refine your old_string or adjust expected_replacements.'
            )

        replaced_normalized = normalized_text.replace(old, new)

        # Restore original line endings style
        if '\r\n' in raw_text:
            new_text = replaced_normalized.replace('\n', '\r\n')
        elif '\r' in raw_text and '\n' not in raw_text:
            new_text = replaced_normalized.replace('\n', '\r')
        else:
            new_text = replaced_normalized

        # Persist changes
        self._history_manager.add_history(path, raw_text)
        self.write_file(path, new_text)

        success_message = f'Replaced {count} occurrence(s) in {path}.\nReview the changes and ensure they are as expected.'
        return CLIResult(
            output=success_message,
            path=str(path),
            prev_exist=True,
            old_content=raw_text,
            new_content=new_text,
        )
