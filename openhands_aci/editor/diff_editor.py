from difflib import SequenceMatcher
from pathlib import Path

from .editor import OHEditor  # Import the base class
from .exceptions import ToolError
from .results import CLIResult

# Fenced diff helper methods adapted from Aider / OpenHands runtime/utils/edit.py
# Original licensed under Apache 2.0: http://www.apache.org/licenses/LICENSE-2.0


class OHDiffEditor(OHEditor):
    """
    An editor that extends OHEditor with Fenced Diff (SEARCH/REPLACE) capabilities,
    while leveraging the base class's history management for undo functionality.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # History manager etc. are initialized by the base class

    # === Fenced Diff Helper Methods ===

    def _fenced_exact_replace(
        self, whole_lines: list[str], part_lines: list[str], replace_lines: list[str]
    ) -> str | None:
        """Attempts to find an exact match of part_lines within whole_lines and replace it."""
        part_tup = tuple(part_lines)
        part_len = len(part_lines)

        if not part_len:
            return None

        for i in range(len(whole_lines) - part_len + 1):
            whole_tup = tuple(whole_lines[i : i + part_len])
            if part_tup == whole_tup:
                res_lines = (
                    whole_lines[:i] + replace_lines + whole_lines[i + part_len :]
                )
                res = ''.join(res_lines)
                # Ensure the result ends with a newline if the original or replacement did
                # or if the original file ended with one.
                if (
                    (part_lines and part_lines[-1].endswith('\n'))
                    or (replace_lines and replace_lines[-1].endswith('\n'))
                    or (whole_lines and whole_lines[-1].endswith('\n'))
                ):
                    if not res.endswith('\n'):
                        res += '\n'
                return res
        return None

    def _fenced_match_but_for_leading_whitespace(
        self, whole_lines: list[str], part_lines: list[str]
    ) -> str | None:
        """Checks if part_lines matches whole_lines ignoring consistent leading whitespace."""
        num = len(whole_lines)
        if len(part_lines) != num:
            return None

        # Check if the content matches after stripping leading whitespace
        if not all(
            whole_lines[i].lstrip() == part_lines[i].lstrip() for i in range(num)
        ):
            return None

        # Check if the leading whitespace difference is consistent
        leading_diffs = set()
        for i in range(num):
            if whole_lines[i].strip():  # Only consider lines with content
                whole_lead = whole_lines[i][
                    : len(whole_lines[i]) - len(whole_lines[i].lstrip())
                ]
                part_lead = part_lines[i][
                    : len(part_lines[i]) - len(part_lines[i].lstrip())
                ]
                # Ensure part line's leading whitespace is a prefix of whole line's
                if not whole_lead.startswith(part_lead):
                    return None
                leading_diffs.add(whole_lead[len(part_lead) :])

        if len(leading_diffs) > 1:
            # Inconsistent leading whitespace difference
            return None
        elif len(leading_diffs) == 1:
            # Consistent difference found
            return leading_diffs.pop()
        else:
            # No difference, or only whitespace lines
            # Check if any part line had *more* whitespace than the whole line (invalid)
            for i in range(num):
                if whole_lines[i].strip():
                    whole_lead_len = len(whole_lines[i]) - len(whole_lines[i].lstrip())
                    part_lead_len = len(part_lines[i]) - len(part_lines[i].lstrip())
                    if part_lead_len > whole_lead_len:
                        return None
            # If we passed the check above, it means the leading whitespace is identical or only differs on empty lines
            return ''

    def _fenced_whitespace_flexible_replace(
        self, whole_lines: list[str], part_lines: list[str], replace_lines: list[str]
    ) -> str | None:
        """Attempts to find part_lines in whole_lines ignoring consistent leading whitespace."""
        num_part_lines = len(part_lines)
        if not num_part_lines:
            return None

        for i in range(len(whole_lines) - num_part_lines + 1):
            chunk_to_check = whole_lines[i : i + num_part_lines]
            common_leading_whitespace = self._fenced_match_but_for_leading_whitespace(
                chunk_to_check, part_lines
            )

            if common_leading_whitespace is not None:
                # Match found! Apply the replacement with the correct leading whitespace.
                adjusted_replace_lines = [
                    common_leading_whitespace + rline if rline.strip() else rline
                    for rline in replace_lines
                ]
                res_lines = (
                    whole_lines[:i]
                    + adjusted_replace_lines
                    + whole_lines[i + num_part_lines :]
                )
                res = ''.join(res_lines)
                # Ensure trailing newline consistency (similar to _exact_replace)
                if (
                    (part_lines and part_lines[-1].endswith('\n'))
                    or (replace_lines and replace_lines[-1].endswith('\n'))
                    or (whole_lines and whole_lines[-1].endswith('\n'))
                ):
                    if not res.endswith('\n'):
                        res += '\n'
                return res
        return None

    def _fenced_find_most_similar_block(
        self, content: str, search_block: str, context_lines: int = 5
    ) -> str:
        """Finds the block in content most similar to search_block."""
        if not search_block.strip() or not content.strip():
            return ''

        search_lines = search_block.splitlines()
        content_lines = content.splitlines()
        search_len = len(search_lines)

        if not search_len or not content_lines:
            return ''

        # Use SequenceMatcher to find the best matching block
        seq_matcher = SequenceMatcher(None, content_lines, search_lines, autojunk=True)
        best_match_info = seq_matcher.find_longest_match(
            0, len(content_lines), 0, search_len
        )

        # Use get_matching_blocks to find potentially better, slightly shorter matches
        matching_blocks = seq_matcher.get_matching_blocks()
        best_ratio = 0.0
        best_match_start = -1
        best_match_len = 0

        for block in matching_blocks:
            current_ratio = block.size / search_len
            if current_ratio > best_ratio:
                if block.size / search_len > 0.5:  # Heuristic threshold
                    best_ratio = current_ratio
                    best_match_start = block.a
                    best_match_len = block.size

        if best_match_start == -1 and best_match_info.size > 0:
            best_match_start = best_match_info.a
            best_match_len = best_match_info.size
            best_ratio = best_match_info.size / search_len

        if best_ratio < 0.3:  # Similarity threshold
            return ''

        best_match_end = best_match_start + search_len
        context_start = max(0, best_match_start - context_lines)
        context_end = min(len(content_lines), best_match_end + context_lines)
        context_snippet_lines = content_lines[context_start:context_end]

        indicator_prefix = '> '
        result_lines = []
        for idx, line in enumerate(context_snippet_lines):
            actual_line_num = context_start + idx
            if best_match_start <= actual_line_num < best_match_start + best_match_len:
                result_lines.append(indicator_prefix + line)
            else:
                result_lines.append('  ' + line)

        return '\n'.join(result_lines)

    # === Main Fenced Replace Method ===

    def fenced_replace(self, path: Path, search: str, replace: str) -> CLIResult:
        """
        Implement Fenced Diff (SEARCH/REPLACE) edit logic.
        """
        self.validate_path('view', path)  # Use 'view' context for basic path validation
        if not path.exists():
            if not search.strip():
                # Create file if search is empty
                self.write_file(path, replace)
                # Note: OHEditor doesn't add history for 'create', so we won't either for consistency
                return CLIResult(
                    path=str(path),
                    new_content=replace,
                    prev_exist=False,
                    output=f'File created successfully at: {path}',
                )
            else:
                raise ToolError(f'File not found: {path}')
        if path.is_dir():
            raise ToolError(
                f'Path is a directory, cannot perform fenced replace: {path}'
            )

        self.validate_file(path)  # Check size, binary etc.

        original_content = self.read_file(path)  # Reads with encoding detection

        # Handle Empty Search Block (Append)
        if not search.strip():
            append_content = replace
            if original_content and not original_content.endswith('\n'):
                original_content_with_newline = original_content + '\n'
            else:
                original_content_with_newline = original_content

            new_content_str = original_content_with_newline + append_content
            # Save history *before* writing
            self._history_manager.add_history(path, original_content)
            self.write_file(path, new_content_str)
            return CLIResult(
                output=f'Appended content to {path}',
                path=str(path),
                old_content=original_content,
                new_content=new_content_str,
                prev_exist=True,
            )

        # Prepare lines for replacement logic
        original_lines = original_content.splitlines(keepends=True)
        search_lines = search.splitlines(keepends=True)
        replace_lines = replace.splitlines(keepends=True)

        if search and not search_lines:
            search_lines = ['\n'] * search.count('\n') + (
                [''] if not search.endswith('\n') else []
            )
        if replace and not replace_lines:
            replace_lines = ['\n'] * replace.count('\n') + (
                [''] if not replace.endswith('\n') else []
            )
        if not replace:
            replace_lines = []

        # Attempt 1: Exact match
        new_content_str = self._fenced_exact_replace(
            original_lines, search_lines, replace_lines
        )

        # Attempt 2: Whitespace flexible match
        if new_content_str is None:
            new_content_str = self._fenced_whitespace_flexible_replace(
                original_lines, search_lines, replace_lines
            )

        # Handle errors (search not found)
        if new_content_str is None:
            error_message = (
                f'Failed to apply fenced diff edit: The specified SEARCH block was not found exactly '
                f'or with flexible whitespace in {path}.\n'
                'SEARCH block:\n```\n' + search + '\n```\n'
            )
            similar_block = self._fenced_find_most_similar_block(
                original_content, search
            )
            if similar_block:
                error_message += (
                    'Did you mean to match something like this block from the file?\n'
                    '(Lines starting with ">" indicate the potential match area):\n'
                    '```\n' + similar_block + '\n```\n'
                )
            error_message += (
                'Please ensure the SEARCH block matches the existing code exactly '
                '(including indentation and whitespace) or uses consistent indentation '
                'if whitespace differs.'
            )
            raise ToolError(error_message)

        # Save history *before* writing
        self._history_manager.add_history(path, original_content)

        # Write modified content
        self.write_file(path, new_content_str)

        # Return success result
        return CLIResult(
            output=f'Applied fenced diff edit to {path}',
            path=str(path),
            old_content=original_content,
            new_content=new_content_str,
            prev_exist=True,
        )

    # Inherits __call__, view, insert, str_replace, undo_edit, etc. from OHEditor
    # Only fenced_replace is added specifically.
