import json

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
    path: str | None = None,
    file_text: str | None = None,
    view_range: list[int] | None = None,
    old_str: str | None = None,
    new_str: str | None = None,
    insert_line: int | None = None,
    symbol_name: str | None = None,
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
            symbol_name=symbol_name,
            enable_linting=enable_linting,
        )
    except ToolError as e:
        return _make_api_tool_result(ToolResult(error=e.message))

    formatted_output_and_error = _make_api_tool_result(result)
    return f"""<oh_aci_output>
{json.dumps(result.to_dict(extra_field={'formatted_output_and_error': formatted_output_and_error}), indent=2)}
</oh_aci_output>"""
