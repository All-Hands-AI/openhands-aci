"""Tests for peak memory usage in file operations."""

import os
import resource
import tempfile
from pathlib import Path

import psutil
import pytest
from memory_profiler import profile

from openhands_aci.editor import file_editor


def get_memory_info():
    """Get current and peak memory usage in bytes."""
    process = psutil.Process(os.getpid())
    rss = process.memory_info().rss
    peak_rss = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    )  # Convert KB to bytes
    return {
        'rss': rss,
        'peak_rss': peak_rss,
        'max': max(rss, peak_rss),
    }


def create_test_file(path: Path, size_mb: float = 5.0):
    """Create a test file of given size (default: 5MB)."""
    line_size = 100  # bytes per line approximately
    num_lines = int((size_mb * 1024 * 1024) // line_size)

    print(f'\nCreating test file with {num_lines} lines...')
    with open(path, 'w') as f:
        for i in range(num_lines):
            f.write(f'Line {i}: ' + 'x' * (line_size - 10) + '\n')

    actual_size = os.path.getsize(path)
    print(f'File created, size: {actual_size / 1024 / 1024:.2f} MB')
    return actual_size


def set_memory_limit(file_size: int, multiplier: float = 2.0):
    """Set memory limit to multiplier * file_size."""
    # Add base memory for pytest and other processes (100MB)
    base_memory = 100 * 1024 * 1024  # 100MB
    memory_limit = int(file_size * multiplier + base_memory)
    try:
        # Get current limits
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        # Only set limit if it's higher than current usage
        current_usage = psutil.Process().memory_info().rss
        if memory_limit > current_usage:
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, hard))
            print(f'Memory limit set to {memory_limit / 1024 / 1024:.2f} MB')
        else:
            print(
                f'Warning: Current memory usage ({current_usage / 1024 / 1024:.2f} MB) higher than limit ({memory_limit / 1024 / 1024:.2f} MB)'
            )
    except Exception as e:
        print(f'Warning: Could not set memory limit: {str(e)}')
    return memory_limit


def check_memory_usage(initial_memory: int, file_size: int, operation: str):
    """Check if memory usage is within acceptable limits."""
    current = get_memory_info()
    memory_growth = current['max'] - initial_memory
    print(f'Peak memory growth: {memory_growth / 1024 / 1024:.2f} MB')

    # Memory growth should be reasonable
    # Allow up to 2x file size for temporary buffers plus 50MB for Python overhead
    overhead = 50 * 1024 * 1024  # 50MB
    max_growth = int(file_size * 2 + overhead)
    assert memory_growth < max_growth, (
        f'Peak memory growth too high for {operation}: {memory_growth / 1024 / 1024:.2f} MB '
        f'(limit: {max_growth / 1024 / 1024:.2f} MB)'
    )


def test_str_replace_peak_memory():
    """Test that str_replace operation has reasonable peak memory usage."""
    with tempfile.NamedTemporaryFile() as temp_file:
        path = Path(temp_file.name)
        file_size = create_test_file(path)

        # Force Python to release file handles and clear buffers
        import gc

        gc.collect()

        # Get initial memory usage
        initial = get_memory_info()
        print(f'Initial memory usage: {initial["rss"] / 1024 / 1024:.2f} MB')

        # Set memory limit
        set_memory_limit(file_size)

        # Perform str_replace operation
        try:
            _ = file_editor(
                command='str_replace',
                path=path,
                old_str='Line 5000',  # Replace a line in the middle
                new_str='Modified line',
                enable_linting=False,
            )
        except MemoryError:
            pytest.fail('Memory limit exceeded - peak memory usage too high')
        except Exception as e:
            if 'Cannot allocate memory' in str(e):
                pytest.fail('Memory limit exceeded - peak memory usage too high')
            raise

        check_memory_usage(initial['max'], file_size, 'str_replace')


@profile
def test_insert_peak_memory():
    """Test that insert operation has reasonable peak memory usage."""
    with tempfile.NamedTemporaryFile() as temp_file:
        path = Path(temp_file.name)
        file_size = create_test_file(path)

        process = psutil.Process(os.getpid())
        print('Memory details before operation:')
        print(f'RSS: {process.memory_info().rss / 1024 / 1024:.2f} MB')
        print(f'VMS: {process.memory_info().vms / 1024 / 1024:.2f} MB')
        print(f'Shared: {process.memory_info().shared / 1024 / 1024:.2f} MB')

        # Force Python to release file handles and clear buffers
        import gc

        gc.collect()

        # Get initial memory usage
        initial = get_memory_info()
        print(f'Initial memory usage: {initial["rss"] / 1024 / 1024:.2f} MB')

        # Set memory limit
        set_memory_limit(file_size)

        # Perform insert operation
        try:
            _ = file_editor(
                command='insert',
                path=path,
                insert_line=5000,  # Insert in the middle
                new_str='New line inserted\n' * 10,
                enable_linting=False,
            )
        except MemoryError as e:
            print(f'Detailed error info: {str(e)}')
            pytest.fail('Memory limit exceeded - peak memory usage too high')
        except Exception as e:
            print(f'Detailed error info: {str(e)}')
            if 'Cannot allocate memory' in str(e):
                pytest.fail('Memory limit exceeded - peak memory usage too high')
            raise

        check_memory_usage(initial['max'], file_size, 'insert')
        assert 1 + 1 == 3


def test_view_peak_memory():
    """Test that view operation has reasonable peak memory usage."""
    with tempfile.NamedTemporaryFile() as temp_file:
        path = Path(temp_file.name)
        file_size = create_test_file(path)

        # Force Python to release file handles and clear buffers
        import gc

        gc.collect()

        # Get initial memory usage
        initial = get_memory_info()
        print(f'Initial memory usage: {initial["rss"] / 1024 / 1024:.2f} MB')

        # Set memory limit
        set_memory_limit(file_size)

        # Test viewing specific lines
        try:
            _ = file_editor(
                command='view',
                path=path,
                view_range=[5000, 5100],  # View 100 lines from middle
                enable_linting=False,
            )
        except MemoryError:
            pytest.fail('Memory limit exceeded - peak memory usage too high')
        except Exception as e:
            if 'Cannot allocate memory' in str(e):
                pytest.fail('Memory limit exceeded - peak memory usage too high')
            raise

        check_memory_usage(initial['max'], file_size, 'view')


def test_view_full_file_peak_memory():
    """Test that viewing entire file has reasonable peak memory usage."""
    with tempfile.NamedTemporaryFile() as temp_file:
        path = Path(temp_file.name)
        file_size = create_test_file(path, size_mb=5.0)  # Smaller file for full view

        # Force Python to release file handles and clear buffers
        import gc

        gc.collect()

        # Get initial memory usage
        initial = get_memory_info()
        print(f'Initial memory usage: {initial["rss"] / 1024 / 1024:.2f} MB')

        # Set memory limit
        set_memory_limit(file_size)

        # Test viewing entire file
        try:
            _ = file_editor(
                command='view',
                path=path,
                enable_linting=False,
            )
        except MemoryError:
            pytest.fail('Memory limit exceeded - peak memory usage too high')
        except Exception as e:
            if 'Cannot allocate memory' in str(e):
                pytest.fail('Memory limit exceeded - peak memory usage too high')
            raise

        check_memory_usage(initial['max'], file_size, 'view_full')


if __name__ == '__main__':
    test_insert_peak_memory()
    # test_view_peak_memory()
    # test_view_full_file_peak_memory()
    # test_str_replace_peak_memory()
