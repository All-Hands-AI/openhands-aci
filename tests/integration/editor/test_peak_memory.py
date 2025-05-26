"""Tests for peak memory usage in file operations."""

import os
import platform
import tempfile
from pathlib import Path

import psutil
import pytest

from openhands_aci.editor import file_editor

# Skip all tests in this module on non-Unix platforms
pytestmark = pytest.mark.skipif(
    platform.system() != 'Linux' and platform.system() != 'Darwin',
    reason='Memory usage tests are Unix-specific and require the resource module',
)


def get_memory_info():
    """Get current and peak memory usage in bytes."""
    import resource

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
            f.write(f'Line {i}: ' + 'x' * (line_size - 30) + '\n')

    actual_size = os.path.getsize(path)
    print(f'File created, size: {actual_size / 1024 / 1024:.2f} MB')
    return actual_size


def set_memory_limit(file_size: int, multiplier: float = 2.0):
    """Set memory limit to multiplier * file_size."""
    import resource

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


def test_insert_peak_memory():
    """Test that insert operation has reasonable peak memory usage."""
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

        # Perform insert operation
        try:
            _ = file_editor(
                command='insert',
                path=path,
                insert_line=5000,  # Insert in the middle
                new_str='New line inserted\n' * 10,
                enable_linting=False,
            )
        except MemoryError:
            pytest.fail('Memory limit exceeded - peak memory usage too high')
        except Exception as e:
            if 'Cannot allocate memory' in str(e):
                pytest.fail('Memory limit exceeded - peak memory usage too high')
            raise

        check_memory_usage(initial['max'], file_size, 'insert')


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


def test_large_history_insert():
    """Test inserting a large amount of data into the history cache."""
    import logging
    import tempfile

    from openhands_aci.editor.history import FileHistoryManager

    # Set up logging
    logging.basicConfig(level=logging.ERROR)

    with tempfile.TemporaryDirectory() as temp_dir:
        history_dir = Path(temp_dir)
        manager = FileHistoryManager(max_history_per_file=1000, history_dir=history_dir)

        # Create a large string (about 1MB)
        large_content = 'x' * (1024 * 1024)

        # Try to insert the large content multiple times
        num_files = 100
        for i in range(num_files):
            try:
                manager.add_history(Path(f'test_file_{i}.txt'), large_content)
            except Exception as e:
                pytest.fail(f'Error occurred on iteration {i}: {str(e)}')

        # Check if we can still retrieve the last entry
        last_content = manager.pop_last_history(Path(f'test_file_{num_files - 1}.txt'))
        assert (
            last_content == large_content
        ), 'Failed to retrieve the last inserted content'

        # Check if the number of cache entries is correct
        cache_entries = list(manager.cache)
        assert (
            len(cache_entries)
            == num_files * 2
            - 1  # The cache entry for file content was removed, only metadata remains
        ), f'Expected {num_files * 2 - 1} cache entries ({num_files - 1} content + {num_files} metadata), but found {len(cache_entries)}'
