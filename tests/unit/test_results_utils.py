from openhands_aci.core.results import ToolResult, maybe_truncate
from openhands_aci.editor.config import MAX_RESPONSE_LEN_CHAR
from openhands_aci.editor.prompts import CONTENT_TRUNCATED_NOTICE


def test_tool_result_bool():
    """Test the boolean value of ToolResult based on output and error."""
    # Case: Both output and error are None
    result = ToolResult()
    assert not bool(result)

    # Case: Only output is set
    result = ToolResult(output='Some output')
    assert bool(result)

    # Case: Only error is set
    result = ToolResult(error='An error occurred')
    assert bool(result)

    # Case: Both output and error are set
    result = ToolResult(output='Some output', error='An error occurred')
    assert bool(result)


def test_maybe_truncate_no_truncation():
    """Test maybe_truncate when content does not exceed the length limit."""
    content = 'Short content'
    result = maybe_truncate(content, truncate_after=MAX_RESPONSE_LEN_CHAR)
    assert result == content  # Should return content as-is


def test_maybe_truncate_with_truncation():
    """Test maybe_truncate when content exceeds the length limit."""
    content = 'a' * (MAX_RESPONSE_LEN_CHAR + 10)
    result = maybe_truncate(content, truncate_after=MAX_RESPONSE_LEN_CHAR)
    assert result == content[:MAX_RESPONSE_LEN_CHAR] + CONTENT_TRUNCATED_NOTICE


def test_maybe_truncate_no_limit():
    """Test maybe_truncate when truncate_after is None."""
    content = 'Content that exceeds the default max length'
    result = maybe_truncate(content, truncate_after=None)
    assert result == content  # No truncation applied when limit is None
