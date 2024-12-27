import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

from .editor import Command, get_args


def parse_view_range(value: str) -> list[int]:
    try:
        start, end = map(int, value.split(','))
        return [start, end]
    except ValueError:
        raise argparse.ArgumentTypeError(
            'view-range must be two comma-separated integers, e.g. "1,10"'
        )


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='OpenHands Editor CLI - A tool for viewing and editing files'
    )
    parser.add_argument(
        'command',
        type=str,
        choices=list(get_args(Command)),
        help='The command to execute',
    )
    parser.add_argument(
        'path',
        type=str,
        help='Path to the file or directory to operate on',
    )
    parser.add_argument(
        '--file-text',
        type=str,
        help='Content for the file when using create command',
    )
    parser.add_argument(
        '--view-range',
        type=parse_view_range,
        help='Line range to view in format "start,end", e.g. "1,10"',
    )
    parser.add_argument(
        '--old-str',
        type=str,
        help='String to replace when using str_replace command',
    )
    parser.add_argument(
        '--new-str',
        type=str,
        help='New string to insert when using str_replace or insert commands',
    )
    parser.add_argument(
        '--insert-line',
        type=int,
        help='Line number after which to insert when using insert command',
    )
    parser.add_argument(
        '--enable-linting',
        action='store_true',
        help='Enable linting for file modifications',
    )
    parser.add_argument(
        '--raw',
        action='store_true',
        help='Output raw JSON response instead of formatted text',
    )
    return parser


def extract_result(output: str) -> dict[str, Any]:
    match = re.search(
        r'<oh_aci_output_[0-9a-f]{32}>(.*?)</oh_aci_output_[0-9a-f]{32}>',
        output,
        re.DOTALL,
    )
    assert match, f'Output does not contain the expected <oh_aci_output_> tags in the correct format: {output}'
    result_dict = json.loads(match.group(1))
    return result_dict


def main() -> NoReturn:
    parser = create_parser()
    args = parser.parse_args()

    # Import here to avoid circular imports
    from . import file_editor

    try:
        output = file_editor(
            command=args.command,
            path=str(Path(args.path).absolute()),
            file_text=args.file_text,
            view_range=args.view_range,
            old_str=args.old_str,
            new_str=args.new_str,
            insert_line=args.insert_line,
            enable_linting=args.enable_linting,
        )

        result = extract_result(output)
        print(result['formatted_output_and_error'])
        sys.exit(0)
    except Exception as e:
        print(f'ERROR: {str(e)}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
