import os
import unittest

from openhands_aci.editor.md_converter import MarkdownConverter


class TestAudioIntegration(unittest.TestCase):
    """Integration tests for audio file conversion through MarkdownConverter."""

    def setUp(self):
        """Set up test fixtures."""
        self.converter = MarkdownConverter()
        self.test_data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data',
            'audio',
        )

    def test_markdown_converter_wav_file(self):
        """Test MarkdownConverter with WAV file."""
        wav_file = os.path.join(self.test_data_dir, 'test.wav')
        if not os.path.exists(wav_file):
            self.skipTest(f'Test WAV file not found: {wav_file}')

        result = self.converter.convert_local(wav_file)
        self.assertIsNotNone(result)
        self.assertIn('Audio Transcript:', result.text_content)
        self.assertIn(
            '1 2', result.text_content
        )  # 3 is not picked up due to the limitation of the ASR API

    def test_markdown_converter_mp3_file(self):
        """Test MarkdownConverter with MP3 file."""
        mp3_file = os.path.join(self.test_data_dir, 'test.mp3')
        if not os.path.exists(mp3_file):
            self.skipTest(f'Test MP3 file not found: {mp3_file}')

        result = self.converter.convert_local(mp3_file)
        self.assertIsNotNone(result)
        self.assertIn('Audio Transcript:', result.text_content)

        if not os.system('which ffmpeg') == 0:
            self.assertIn('ffmpeg/avconv not installed', result.text_content)
        else:
            self.assertIn('1 2', result.text_content)

    def test_markdown_converter_m4a_file(self):
        """Test MarkdownConverter with M4A file."""
        m4a_file = os.path.join(self.test_data_dir, 'test.m4a')
        if not os.path.exists(m4a_file):
            self.skipTest(f'Test M4A file not found: {m4a_file}')

        result = self.converter.convert_local(m4a_file)
        self.assertIsNotNone(result)
        self.assertIn('Audio Transcript:', result.text_content)

        if not os.system('which ffmpeg') == 0:
            self.assertIn('ffmpeg/avconv not installed', result.text_content)
        else:
            self.assertIn('1 2', result.text_content)

    def test_markdown_converter_flac_file(self):
        """Test MarkdownConverter with FLAC file."""
        flac_file = os.path.join(self.test_data_dir, 'test.flac')
        if not os.path.exists(flac_file):
            self.skipTest(f'Test FLAC file not found: {flac_file}')

        result = self.converter.convert_local(flac_file)
        self.assertIsNotNone(result)
        self.assertIn('Audio Transcript:', result.text_content)

        if not os.system('which ffmpeg') == 0:
            self.assertIn('ffmpeg/avconv not installed', result.text_content)
        else:
            self.assertIn('1 2', result.text_content)

    def test_all_audio_formats_produce_similar_output(self):
        """Test that all audio formats produce similar output structure."""
        audio_files = [
            ('test.wav', 'WAV'),
            ('test.mp3', 'MP3'),
            ('test.m4a', 'M4A'),
            ('test.flac', 'FLAC'),
        ]

        results = {}

        for filename, format_name in audio_files:
            file_path = os.path.join(self.test_data_dir, filename)
            if os.path.exists(file_path):
                result = self.converter.convert_local(file_path)
                self.assertIsNotNone(result, f'Failed to convert {format_name} file')
                results[format_name] = result.text_content

                # Check that all results contain the transcript section
                self.assertIn('Audio Transcript:', result.text_content)

                # Check that the result is not empty
                self.assertTrue(len(result.text_content.strip()) > 0)

        # If we have results from multiple formats, they should all contain similar structure
        if len(results) > 1:
            # All should contain the transcript section
            for format_name, content in results.items():
                self.assertIn(
                    '### Audio Transcript:',
                    content,
                    f'{format_name} missing transcript section',
                )

    def test_audio_file_extension_detection(self):
        """Test that audio files are correctly detected by extension."""
        test_cases = [
            ('test.wav', 'WAV'),
            ('test.mp3', 'MP3'),
            ('test.m4a', 'M4A'),
            ('test.flac', 'FLAC'),
        ]

        for filename, format_name in test_cases:
            file_path = os.path.join(self.test_data_dir, filename)
            if os.path.exists(file_path):
                # Test without explicit file_extension parameter
                result = self.converter.convert_local(file_path)
                self.assertIsNotNone(
                    result, f'Failed to auto-detect {format_name} file'
                )

                # Test with explicit file_extension parameter
                _, ext = os.path.splitext(filename)
                result_explicit = self.converter.convert_local(
                    file_path, file_extension=ext
                )
                self.assertIsNotNone(
                    result_explicit,
                    f'Failed to convert {format_name} with explicit extension',
                )

                # Both results should be similar
                self.assertEqual(result.text_content, result_explicit.text_content)


if __name__ == '__main__':
    unittest.main()
