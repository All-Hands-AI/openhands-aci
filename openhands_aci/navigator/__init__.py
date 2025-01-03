from openhands_aci.core.exceptions import ToolError
from openhands_aci.core.results import ToolResult, make_api_tool_result

from .navigator import Command, SymbolNavigator

GLOBAL_NAVIGATOR = SymbolNavigator()


TOOL_DESCRIPTION = """Custom navigation tool for navigating to symbols in a codebase
* If there are multiple symbols with the same name, the tool will print all of them
* The `jump_to_definition` command will print the FULL definition of the symbol, along with the absolute path to the file
* The `find_references` command will print only the file content at the line where the symbol is referenced, along with the absolute path to the file
* It is more preferable to use this tool for user-defined symbols. For built-in symbols, consider using other tools like `grep`
"""

PARAMS_DESCRIPTION = {
    'command': 'The command to run. Allowed options are: `jump_to_definition`, `find_references`.',
    'symbol_name': 'The symbol name to navigate to.',
}


def symbol_navigator(
    command: Command,
    symbol_name: str,
) -> str:
    result: ToolResult | None = None
    try:
        result = GLOBAL_NAVIGATOR(
            command=command,
            symbol_name=symbol_name,
        )
    except ToolError as e:
        result = ToolResult(error=e.message)

    return make_api_tool_result(result)  # Return as default IPython output
