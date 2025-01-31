from pathlib import Path
from typing import Generator, Optional, Tuple


def read_file_chunks(
    path: Path, chunk_size: int = 1024 * 1024
) -> Generator[str, None, None]:
    """Read a file in chunks to reduce memory usage."""
    with open(path, 'r') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def find_string_in_file(path: Path, search_str: str) -> list[int]:
    """Find all occurrences of a string in a file and return line numbers."""
    line_numbers = []
    current_line = 1

    with open(path, 'r') as f:
        # Read line by line to avoid loading entire file
        for line in f:
            if search_str in line:
                line_numbers.append(current_line)
            current_line += 1

    return line_numbers


def replace_string_in_file(path: Path, old_str: str, new_str: str) -> bool:
    """Replace a string in a file using minimal memory."""
    temp_path = path.with_suffix(path.suffix + '.tmp')

    try:
        with open(path, 'r') as src, open(temp_path, 'w') as dst:
            replaced = False

            # Process line by line
            for line in src:
                if old_str in line:
                    dst.write(line.replace(old_str, new_str))
                    replaced = True
                else:
                    dst.write(line)

        # Only replace original file if we actually made a replacement
        if replaced:
            temp_path.replace(path)
        else:
            temp_path.unlink()
            return False

        return True

    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def get_file_lines(
    path: Path, start_line: Optional[int] = None, end_line: Optional[int] = None
) -> Generator[Tuple[int, str], None, None]:
    """Get specific lines from a file using minimal memory."""
    current_line = 1

    with open(path, 'r') as f:
        # Skip lines before start_line
        if start_line is not None and start_line > 1:
            for _ in range(start_line - 1):
                next(f)
                current_line += 1

        # Read and yield requested lines
        for line in f:
            if end_line is not None and current_line > end_line:
                break

            line = line.rstrip('\n')  # Remove trailing newline
            yield current_line, line
            current_line += 1
