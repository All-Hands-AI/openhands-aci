import tempfile
import unittest
from unittest import mock

from openhands_aci.editor.md_converter import Mp3Converter


class TestMp3Converter(unittest.TestCase):
    """Test the Mp3Converter class."""

    def test_pydub_not_available(self):
        """Test that Mp3Converter handles the case when pydub is not available."""
        # Mock the pydub_available flag to be False
        with mock.patch('openhands_aci.editor.md_converter.pydub_available', False):
            converter = Mp3Converter()

            # Create a temporary file with .mp3 extension
            with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
                # Call convert method
                result = converter.convert(temp_file.name, file_extension='.mp3')

                # Check that the result contains the expected message
                assert result is not None
                assert (
                    'Transcription unavailable - ffmpeg/avconv not installed'
                    in result.text_content
                )

    def test_pydub_none(self):
        """Test that Mp3Converter handles the case when pydub is None."""
        # Mock pydub to be None
        with mock.patch('openhands_aci.editor.md_converter.pydub', None):
            converter = Mp3Converter()

            # Create a temporary file with .mp3 extension
            with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
                # Call convert method
                result = converter.convert(temp_file.name, file_extension='.mp3')

                # Check that the result contains the expected message
                assert result is not None
                assert (
                    'Transcription unavailable - ffmpeg/avconv not installed'
                    in result.text_content
                )
