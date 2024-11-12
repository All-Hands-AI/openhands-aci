from .editor import Command, OHEditor
from .exceptions import ToolError
from .results import ToolResult

_GLOBAL_EDITOR = OHEditor()


def _make_api_tool_result(tool_result: ToolResult) -> str:
    """Convert an agent ToolResult to an API ToolResultBlockParam."""
    if tool_result.error:
        return f'ERROR:\n{tool_result.error}'

    assert tool_result.output, 'Expected output in file_editor.'
    return tool_result.output


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
        return _make_api_tool_result(ToolResult(error=e.message))

    return _make_api_tool_result(result)
