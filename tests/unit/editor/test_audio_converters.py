import os
import tempfile
import unittest
from unittest import mock

from openhands_aci.editor.md_converter import (
    FlacConverter,
    M4aConverter,
    Mp3Converter,
    WavConverter,
)


class TestAudioConverters(unittest.TestCase):
    """Test all audio converter classes."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data',
            'audio',
        )

    def test_wav_converter_with_real_file(self):
        """Test WavConverter with a real WAV file."""
        wav_file = os.path.join(self.test_data_dir, 'test.wav')
        if not os.path.exists(wav_file):
            self.skipTest(f'Test WAV file not found: {wav_file}')

        converter = WavConverter()
        result = converter.convert(wav_file, file_extension='.wav')

        self.assertIsNotNone(result)
        self.assertIn('Audio Transcript:', result.text_content)

    def test_mp3_converter_with_real_file(self):
        """Test Mp3Converter with a real MP3 file."""
        mp3_file = os.path.join(self.test_data_dir, 'test.mp3')
        if not os.path.exists(mp3_file):
            self.skipTest(f'Test MP3 file not found: {mp3_file}')

        converter = Mp3Converter()
        result = converter.convert(mp3_file, file_extension='.mp3')

        self.assertIsNotNone(result)
        self.assertIn('Audio Transcript:', result.text_content)

    def test_m4a_converter_with_real_file(self):
        """Test M4aConverter with a real M4A file."""
        m4a_file = os.path.join(self.test_data_dir, 'test.m4a')
        if not os.path.exists(m4a_file):
            self.skipTest(f'Test M4A file not found: {m4a_file}')

        converter = M4aConverter()
        result = converter.convert(m4a_file, file_extension='.m4a')

        self.assertIsNotNone(result)
        self.assertIn('Audio Transcript:', result.text_content)

    def test_flac_converter_with_real_file(self):
        """Test FlacConverter with a real FLAC file."""
        flac_file = os.path.join(self.test_data_dir, 'test.flac')
        if not os.path.exists(flac_file):
            self.skipTest(f'Test FLAC file not found: {flac_file}')

        converter = FlacConverter()
        result = converter.convert(flac_file, file_extension='.flac')

        self.assertIsNotNone(result)
        self.assertIn('Audio Transcript:', result.text_content)

    def test_wav_converter_wrong_extension(self):
        """Test that WavConverter returns None for wrong file extension."""
        converter = WavConverter()
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            result = converter.convert(temp_file.name, file_extension='.mp3')
            self.assertIsNone(result)

    def test_mp3_converter_wrong_extension(self):
        """Test that Mp3Converter returns None for wrong file extension."""
        converter = Mp3Converter()
        with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
            result = converter.convert(temp_file.name, file_extension='.wav')
            self.assertIsNone(result)

    def test_m4a_converter_wrong_extension(self):
        """Test that M4aConverter returns None for wrong file extension."""
        converter = M4aConverter()
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            result = converter.convert(temp_file.name, file_extension='.mp3')
            self.assertIsNone(result)

    def test_flac_converter_wrong_extension(self):
        """Test that FlacConverter returns None for wrong file extension."""
        converter = FlacConverter()
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            result = converter.convert(temp_file.name, file_extension='.mp3')
            self.assertIsNone(result)

    def test_mp3_converter_pydub_not_available(self):
        """Test that Mp3Converter handles the case when pydub is not available."""
        with mock.patch('openhands_aci.editor.md_converter.pydub_available', False):
            converter = Mp3Converter()
            with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
                result = converter.convert(temp_file.name, file_extension='.mp3')
                self.assertIsNotNone(result)
                self.assertIn(
                    'Transcription unavailable - ffmpeg/avconv not installed',
                    result.text_content,
                )

    def test_m4a_converter_pydub_not_available(self):
        """Test that M4aConverter handles the case when pydub is not available."""
        with mock.patch('openhands_aci.editor.md_converter.pydub_available', False):
            converter = M4aConverter()
            with tempfile.NamedTemporaryFile(suffix='.m4a') as temp_file:
                result = converter.convert(temp_file.name, file_extension='.m4a')
                self.assertIsNotNone(result)
                self.assertIn(
                    'Transcription unavailable - ffmpeg/avconv not installed',
                    result.text_content,
                )

    def test_flac_converter_pydub_not_available(self):
        """Test that FlacConverter handles the case when pydub is not available."""
        with mock.patch('openhands_aci.editor.md_converter.pydub_available', False):
            converter = FlacConverter()
            with tempfile.NamedTemporaryFile(suffix='.flac') as temp_file:
                result = converter.convert(temp_file.name, file_extension='.flac')
                self.assertIsNotNone(result)
                self.assertIn(
                    'Transcription unavailable - ffmpeg/avconv not installed',
                    result.text_content,
                )

    def test_wav_converter_speech_recognition_error(self):
        """Test that WavConverter handles speech recognition errors gracefully."""
        converter = WavConverter()
        wav_file = os.path.join(self.test_data_dir, 'test.wav')
        if not os.path.exists(wav_file):
            self.skipTest(f'Test WAV file not found: {wav_file}')

        # Mock the speech recognition to raise an exception
        with mock.patch(
            'speech_recognition.Recognizer.recognize_google',
            side_effect=Exception('Test error'),
        ):
            result = converter.convert(wav_file, file_extension='.wav')
            self.assertIsNotNone(result)
            self.assertIn(
                'Error. Could not transcribe this audio.',
                result.text_content,
            )

    def test_mp3_converter_pydub_none(self):
        """Test that Mp3Converter handles the case when pydub is None."""
        with mock.patch('openhands_aci.editor.md_converter.pydub', None):
            converter = Mp3Converter()
            with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
                result = converter.convert(temp_file.name, file_extension='.mp3')
                self.assertIsNotNone(result)
                self.assertIn(
                    'Transcription unavailable - ffmpeg/avconv not installed',
                    result.text_content,
                )

    def test_m4a_converter_pydub_none(self):
        """Test that M4aConverter handles the case when pydub is None."""
        with mock.patch('openhands_aci.editor.md_converter.pydub', None):
            converter = M4aConverter()
            with tempfile.NamedTemporaryFile(suffix='.m4a') as temp_file:
                result = converter.convert(temp_file.name, file_extension='.m4a')
                self.assertIsNotNone(result)
                self.assertIn(
                    'Transcription unavailable - ffmpeg/avconv not installed',
                    result.text_content,
                )

    def test_flac_converter_pydub_none(self):
        """Test that FlacConverter handles the case when pydub is None."""
        with mock.patch('openhands_aci.editor.md_converter.pydub', None):
            converter = FlacConverter()
            with tempfile.NamedTemporaryFile(suffix='.flac') as temp_file:
                result = converter.convert(temp_file.name, file_extension='.flac')
                self.assertIsNotNone(result)
                self.assertIn(
                    'Transcription unavailable - ffmpeg/avconv not installed',
                    result.text_content,
                )

    def test_wav_converter_transcription_error(self):
        """Test WavConverter handles transcription errors gracefully."""
        converter = WavConverter()

        # Mock the _transcribe_audio method to raise an exception
        with mock.patch.object(
            converter, '_transcribe_audio', side_effect=Exception('Test error')
        ):
            wav_file = os.path.join(self.test_data_dir, 'test.wav')
            if not os.path.exists(wav_file):
                self.skipTest(f'Test WAV file not found: {wav_file}')

            result = converter.convert(wav_file, file_extension='.wav')
            self.assertIsNotNone(result)
            self.assertIn(
                'Error. Could not transcribe this audio.', result.text_content
            )

    def test_all_converters_case_insensitive_extensions(self):
        """Test that all converters handle case-insensitive file extensions."""
        test_files = [
            ('test.wav', WavConverter(), '.WAV'),
            ('test.mp3', Mp3Converter(), '.MP3'),
            ('test.m4a', M4aConverter(), '.M4A'),
            ('test.flac', FlacConverter(), '.FLAC'),
        ]

        for filename, converter, extension in test_files:
            file_path = os.path.join(self.test_data_dir, filename)
            if not os.path.exists(file_path):
                self.skipTest(f'Test file not found: {file_path}')

            # Test with uppercase extension
            result = converter.convert(file_path, file_extension=extension)
            self.assertIsNotNone(
                result,
                f'Converter {converter.__class__.__name__} failed with extension {extension}',
            )

    def test_metadata_extraction_mock(self):
        """Test metadata extraction with mocked exiftool."""
        mock_metadata = {
            'Title': 'Test Song',
            'Artist': 'Test Artist',
            'Album': 'Test Album',
            'Duration': '00:02:30',
        }

        test_files = [
            ('test.wav', WavConverter()),
            ('test.mp3', Mp3Converter()),
            ('test.m4a', M4aConverter()),
            ('test.flac', FlacConverter()),
        ]

        for filename, converter in test_files:
            file_path = os.path.join(self.test_data_dir, filename)
            if not os.path.exists(file_path):
                self.skipTest(f'Test file not found: {file_path}')

            with mock.patch.object(
                converter, '_get_metadata', return_value=mock_metadata
            ):
                _, ext = os.path.splitext(filename)
                result = converter.convert(file_path, file_extension=ext)
                self.assertIsNotNone(result)

                # Check that metadata is included in the output
                for key, value in mock_metadata.items():
                    self.assertIn(f'{key}: {value}', result.text_content)


if __name__ == '__main__':
    unittest.main()
