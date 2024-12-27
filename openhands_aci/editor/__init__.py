import json
import uuid

from openhands_aci.core.exceptions import ToolError
from openhands_aci.core.results import ToolResult, make_api_tool_result

from .editor import Command, OHEditor

_GLOBAL_EDITOR = OHEditor()


TOOL_DESCRIPTION = """Custom editing tool for viewing, creating and editing files
* State is persistent across command calls and discussions with the user
* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The `create` command cannot be used if the specified `path` already exists as a file
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
* The `undo_edit` command will revert the last edit made to the file at `path`

Notes for using the `str_replace` command:
* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
* The `new_str` parameter should contain the edited lines that should replace the `old_str`
"""

PARAMS_DESCRIPTION = {
    'command': 'The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.',
    'path': 'Absolute path to file or directory, e.g. `/workspace/file.py` or `/workspace`.',
    'file_text': 'Required parameter of `create` command, with the content of the file to be created.',
    'old_str': 'Required parameter of `str_replace` command containing the string in `path` to replace.',
    'new_str': 'Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.',
    'insert_line': 'Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.',
    'view_range': 'Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.',
}


def file_editor(
    command: Command,
    path: str,
    file_text: str | None = None,
    view_range: list[int] | None = None,
    old_str: str | None = None,
    new_str: str | None = None,
    insert_line: int | None = None,
    enable_linting: bool = False,
) -> str:
    result: ToolResult | None = None
    try:
        result = _GLOBAL_EDITOR(
            command=command,
            path=path,
            file_text=file_text,
            view_range=view_range,
            old_str=old_str,
            new_str=new_str,
            insert_line=insert_line,
            enable_linting=enable_linting,
        )
    except ToolError as e:
        result = ToolResult(error=e.message)

    formatted_output_and_error = make_api_tool_result(result)
    marker_id = uuid.uuid4().hex
    return f"""<oh_aci_output_{marker_id}>
{json.dumps(result.to_dict(extra_field={'formatted_output_and_error': formatted_output_and_error}), indent=2)}
</oh_aci_output_{marker_id}>"""
