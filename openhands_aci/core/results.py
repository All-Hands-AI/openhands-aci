from dataclasses import asdict, dataclass, fields

from ..editor.config import MAX_RESPONSE_LEN_CHAR
from ..editor.prompts import CONTENT_TRUNCATED_NOTICE


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""

    output: str | None = None
    error: str | None = None

    def __bool__(self):
        return any(getattr(self, field.name) for field in fields(self))

    def to_dict(self, extra_field: dict | None = None) -> dict:
        result = asdict(self)

        # Add extra fields if provided
        if extra_field:
            result.update(extra_field)
        return result


@dataclass
class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""

    # Optional fields for file editing commands
    path: str | None = None
    prev_exist: bool = True
    old_content: str | None = None
    new_content: str | None = None


def maybe_truncate(
    content: str, truncate_after: int | None = MAX_RESPONSE_LEN_CHAR
) -> str:
    """
    Truncate content and append a notice if content exceeds the specified length.
    """
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + CONTENT_TRUNCATED_NOTICE
    )


def make_api_tool_result(tool_result: ToolResult) -> str:
    """Convert an agent ToolResult to an API ToolResultBlockParam."""
    if tool_result.error:
        return f'ERROR:\n{tool_result.error}'

    assert tool_result.output, 'Expected output in file_editor.'
    return tool_result.output
