"""Tests for the audio module."""

import os
import tempfile
import wave

from openhands_aci.utils.audio import AudioData, AudioFile, Recognizer


def create_test_wav_file(filename, sample_rate=16000, sample_width=2, duration=1.0):
    """Create a test WAV file with the given parameters."""
    frames = int(duration * sample_rate)

    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)

        # Create silent audio (all zeros)
        wav_file.writeframes(b'\x00' * frames * sample_width)


def test_audio_file():
    """Test the AudioFile class."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_filename = temp_file.name

    try:
        # Create a test WAV file
        create_test_wav_file(temp_filename)

        # Test opening the file
        with AudioFile(temp_filename) as audio_file:
            assert audio_file.SAMPLE_RATE == 16000
            assert audio_file.SAMPLE_WIDTH == 2
            assert audio_file.DURATION == 1.0

            # Test reading from the file
            audio_data = audio_file.stream.read(1024)
            assert isinstance(audio_data, bytes)
            assert len(audio_data) > 0
    finally:
        # Clean up
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)


def test_recognizer_record():
    """Test the Recognizer.record method."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_filename = temp_file.name

    try:
        # Create a test WAV file
        create_test_wav_file(temp_filename)

        # Test recording from the file
        recognizer = Recognizer()
        with AudioFile(temp_filename) as audio_file:
            audio_data = recognizer.record(audio_file)

            # Verify the audio data
            assert isinstance(audio_data, AudioData)
            assert audio_data.sample_rate == 16000
            assert audio_data.sample_width == 2
            assert len(audio_data.frame_data) > 0
    finally:
        # Clean up
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)


def test_audio_data_get_wav_data():
    """Test the AudioData.get_wav_data method."""
    # Create some dummy audio data
    frame_data = b'\x00\x00' * 1000  # 1000 samples of silence (16-bit)
    sample_rate = 16000
    sample_width = 2

    # Create an AudioData instance
    audio_data = AudioData(frame_data, sample_rate, sample_width)

    # Test getting WAV data
    wav_data = audio_data.get_wav_data()
    assert isinstance(wav_data, bytes)
    assert len(wav_data) > len(frame_data)  # WAV data includes header

    # Test getting WAV data with conversion
    wav_data_converted = audio_data.get_wav_data(convert_rate=8000, convert_width=1)
    assert isinstance(wav_data_converted, bytes)
    assert len(wav_data_converted) != len(wav_data)  # Different due to conversion
