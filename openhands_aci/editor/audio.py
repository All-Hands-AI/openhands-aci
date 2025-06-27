
"""
Audio processing utilities for the speech recognition functionality.
"""
import io
import os
import platform
import subprocess
import tempfile
import wave
from typing import Optional, Tuple, Union

class AudioData:
    """
    Represents audio data with a specific sample rate, sample width, and number of channels.

    Args:
        data: Raw audio data
        sample_rate: Sample rate in Hz
        sample_width: Sample width in bytes
    """

    def __init__(self, data: bytes, sample_rate: int, sample_width: int):
        self.data = data
        self.sample_rate = sample_rate
        self.sample_width = sample_width

    def get_flac_data(
        self,
        convert_rate: Optional[int] = None,
        convert_width: Optional[int] = None,
    ) -> bytes:
        """
        Converts the audio data to FLAC format.

        Args:
            convert_rate: Optional target sample rate
            convert_width: Optional target sample width

        Returns:
            FLAC-encoded audio data
        """
        if convert_rate is None:
            convert_rate = self.sample_rate

        if convert_width is None:
            convert_width = self.sample_width

        # Convert to WAV first
        wav_data = self._convert_to_wav(
            sample_rate=convert_rate,
            sample_width=convert_width,
        )

        # Then convert to FLAC
        return self._convert_to_flac(wav_data)

    def _convert_to_wav(
        self, sample_rate: int, sample_width: int
    ) -> bytes:
        """
        Converts the audio data to WAV format.

        Args:
            sample_rate: Target sample rate
            sample_width: Target sample width

        Returns:
            WAV-encoded audio data
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name

        try:
            with wave.open(temp_wav_path, "w") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(self.data)

            with open(temp_wav_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(temp_wav_path):
                os.unlink(temp_wav_path)

    def _convert_to_flac(self, wav_data: bytes) -> bytes:
        """
        Converts WAV data to FLAC format.

        Args:
            wav_data: WAV-encoded audio data

        Returns:
            FLAC-encoded audio data
        """
        flac_converter = get_flac_converter()

        if os.name == "nt":  # Windows
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                [flac_converter, "--stdin-name=-", "--output-name=-", "--force"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startup_info=startup_info,
            )
        else:  # Unix-like
            process = subprocess.Popen(
                [flac_converter, "--stdin-name=-", "--output-name=-", "--force"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        flac_data, _ = process.communicate(wav_data)
        return flac_data

def get_flac_converter() -> str:
    """
    Gets the path to the FLAC converter executable.

    Returns:
        Path to the FLAC converter executable
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        if machine.startswith("amd64") or machine.startswith("x86_64"):
            return os.path.join(os.path.dirname(__file__), "flac-win64.exe")
        else:
            return os.path.join(os.path.dirname(__file__), "flac-win32.exe")
    elif system == "darwin":  # macOS
        return os.path.join(os.path.dirname(__file__), "flac-mac")
    elif system == "linux":
        if machine.startswith("amd64") or machine.startswith("x86_64"):
            return os.path.join(os.path.dirname(__file__), "flac-linux-x86_64")
        elif machine.startswith("arm") or machine.startswith("aarch64"):
            return os.path.join(os.path.dirname(__file__), "flac-linux-arm")
        else:
            return os.path.join(os.path.dirname(__file__), "flac-linux-x86")
    else:
        raise NotImplementedError(f"Unsupported platform: {system}/{machine}")
