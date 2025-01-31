import os
import tempfile
import psutil
import pytest
from pathlib import Path

from openhands_aci.editor.editor import OHEditor

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def test_memory_usage_large_file():
    """Test that memory usage is reasonable when handling large files"""
    editor = OHEditor()
    
    # Create a temporary large file (10MB)
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_path = Path(f.name)
        # Write 10MB of data (each line is 100 chars, so 100K lines)
        for i in range(100_000):
            f.write(f"Line {i:06d}: " + "x" * 90 + "\n")
    
    try:
        # Measure baseline memory
        baseline_memory = get_memory_usage()
        
        # Test viewing file
        result = editor.view(temp_path)
        view_memory = get_memory_usage()
        view_increase = view_memory - baseline_memory
        assert view_increase < 50, f"Memory increase for view was {view_increase:.1f}MB"
        
        # Test replacing a string
        old_str = "Line 050000: " + "x" * 90
        new_str = "New line 50k: " + "y" * 90
        result = editor.str_replace(temp_path, old_str, new_str, enable_linting=False)
        replace_memory = get_memory_usage()
        replace_increase = replace_memory - baseline_memory
        assert replace_increase < 50, f"Memory increase for replace was {replace_increase:.1f}MB"
        
        # Test inserting a string
        insert_str = "Inserted line\n"
        result = editor.insert(temp_path, 50000, insert_str, enable_linting=False)
        insert_memory = get_memory_usage()
        insert_increase = insert_memory - baseline_memory
        assert insert_increase < 50, f"Memory increase for insert was {insert_increase:.1f}MB"
        
    finally:
        # Clean up
        temp_path.unlink()