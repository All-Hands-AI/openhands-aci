"""Tests for the encoding module."""

import os
import tempfile
from pathlib import Path
import unittest

from openhands_aci.editor.encoding import EncodingManager


class TestEncoding(unittest.TestCase):
    """Test the encoding detection and handling."""

    def test_ascii_detection_returns_utf8(self):
        """Test that ASCII files are detected as UTF-8."""
        # Create a test file with ASCII content
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as f:
            f.write("This is a test file with ASCII content\n")
            ascii_file_path = f.name

        try:
            # Initialize the encoding manager
            encoding_manager = EncodingManager()

            # Detect encoding for ASCII file
            ascii_encoding = encoding_manager.get_encoding(Path(ascii_file_path))
            
            # Verify that ASCII files are detected as UTF-8
            self.assertEqual(ascii_encoding.lower(), 'utf-8')
        finally:
            # Clean up
            os.unlink(ascii_file_path)


if __name__ == '__main__':
    unittest.main()