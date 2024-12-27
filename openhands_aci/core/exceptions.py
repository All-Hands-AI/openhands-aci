class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message


class MultiCommandToolParameterMissingError(ToolError):
    """Raised when a required parameter is missing for a tool command."""

    def __init__(self, command, parameter):
        self.command = command
        self.parameter = parameter
        self.message = f'Parameter `{parameter}` is required for command: {command}.'


class ToolParameterInvalidError(ToolError):
    """Raised when a parameter is invalid for a tool command."""

    def __init__(self, parameter, value, hint=None):
        self.parameter = parameter
        self.value = value
        self.message = (
            f'Invalid `{parameter}` parameter: {value}. {hint}'
            if hint
            else f'Invalid `{parameter}` parameter: {value}.'
        )
