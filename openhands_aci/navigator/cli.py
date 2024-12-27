import argparse
import sys
from typing import NoReturn

from .navigator import Command, get_args


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='OpenHands Navigator CLI - A tool for navigating in a codebase'
    )
    parser.add_argument(
        'command',
        type=str,
        choices=list(get_args(Command)),
        help='The command to execute',
    )
    parser.add_argument(
        'symbol_name',
        type=str,
        help='The symbol name to navigate to',
    )
    return parser


def main() -> NoReturn:
    parser = create_parser()
    args = parser.parse_args()

    # Import here to avoid circular imports
    from . import symbol_navigator

    try:
        result = symbol_navigator(
            command=args.command,
            symbol_name=args.symbol_name,
        )

        print(result)
        sys.exit(0)
    except Exception as e:
        print(f'ERROR: {str(e)}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
