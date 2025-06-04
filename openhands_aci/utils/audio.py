"""
Minimal implementation of audio processing functionality.
This module provides a minimal implementation of the functionality from the
speech_recognition library that is used by openhands-aci.
"""

import audioop
import io
import json
import os
import wave
from typing import Dict, List, Literal, Optional, TypedDict, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class AudioSource:
    """Base class for audio sources."""
    def __init__(self):
        self.stream = None
        self.SAMPLE_RATE = None
        self.SAMPLE_WIDTH = None
        self.CHUNK = None


class AudioFile(AudioSource):
    """
    Creates a new ``AudioFile`` instance given a WAV audio file ``filename_or_fileobject``.
    Subclass of ``AudioSource``.

    If ``filename_or_fileobject`` is a string, then it is interpreted as a path to an audio file
    on the filesystem. Otherwise, ``filename_or_fileobject`` should be a file-like object.

    Note that functions that read from the audio (such as ``recognizer_instance.record``)
    will move ahead in the stream.
    """

    def __init__(self, filename_or_fileobject):
        super().__init__()
        assert isinstance(filename_or_fileobject, (str, bytes)) or hasattr(filename_or_fileobject, "read"), \
            "Given audio file must be a filename string or a file-like object"
        self.filename_or_fileobject = filename_or_fileobject
        self.DURATION = None
        self.audio_reader = None
        self.FRAME_COUNT = None

    def __enter__(self):
        assert self.stream is None, "This audio source is already inside a context manager"
        try:
            # attempt to read the file as WAV
            self.audio_reader = wave.open(self.filename_or_fileobject, "rb")
        except (wave.Error, EOFError):
            raise ValueError("Audio file could not be read as PCM WAV; check if file is corrupted or in another format")
        
        assert 1 <= self.audio_reader.getnchannels() <= 2, "Audio must be mono or stereo"
        self.SAMPLE_WIDTH = self.audio_reader.getsampwidth()
        self.SAMPLE_RATE = self.audio_reader.getframerate()
        self.CHUNK = 4096
        self.FRAME_COUNT = self.audio_reader.getnframes()
        self.DURATION = self.FRAME_COUNT / float(self.SAMPLE_RATE)
        self.stream = AudioFileStream(self.audio_reader)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not hasattr(self.filename_or_fileobject, "read"):  # only close the file if it was opened by this class
            self.audio_reader.close()
        self.stream = None
        self.DURATION = None


class AudioFileStream:
    """A file-like object that reads from an AudioFile."""
    
    def __init__(self, audio_reader):
        self.audio_reader = audio_reader

    def read(self, size=-1):
        buffer = self.audio_reader.readframes(self.audio_reader.getnframes() if size == -1 else size)
        if not isinstance(buffer, bytes):
            buffer = b""
        
        # Convert stereo to mono if needed
        if self.audio_reader.getnchannels() != 1:
            buffer = audioop.tomono(buffer, self.audio_reader.getsampwidth(), 1, 1)
        
        return buffer


class AudioData:
    """
    Creates a new ``AudioData`` instance, which represents mono audio data.

    The raw audio data is specified by ``frame_data``, which is a sequence of bytes
    representing audio samples. This is the frame data structure used by the PCM WAV format.

    The width of each sample, in bytes, is specified by ``sample_width``.
    Each group of ``sample_width`` bytes represents a single audio sample.

    The audio data is assumed to have a sample rate of ``sample_rate`` samples per second (Hertz).
    """

    def __init__(self, frame_data, sample_rate, sample_width):
        assert sample_rate > 0, "Sample rate must be a positive integer"
        assert sample_width % 1 == 0 and 1 <= sample_width <= 4, \
            "Sample width must be between 1 and 4 inclusive"
        self.frame_data = frame_data
        self.sample_rate = sample_rate
        self.sample_width = int(sample_width)

    def get_flac_data(self, convert_rate=None, convert_width=None):
        """
        Returns a byte string representing the contents of a FLAC file containing the audio
        represented by the ``AudioData`` instance.

        For simplicity, this implementation just returns the WAV data since we're only
        using this for the Google Speech API which also accepts WAV data.
        """
        return self.get_wav_data(convert_rate, convert_width)

    def get_wav_data(self, convert_rate=None, convert_width=None):
        """
        Returns a byte string representing the contents of a WAV file containing the audio
        represented by the ``AudioData`` instance.
        """
        raw_data = self.get_raw_data(convert_rate, convert_width)
        sample_rate = self.sample_rate if convert_rate is None else convert_rate
        sample_width = self.sample_width if convert_width is None else convert_width

        # generate the WAV file contents
        with io.BytesIO() as wav_file:
            wav_writer = wave.open(wav_file, "wb")
            try:
                wav_writer.setframerate(sample_rate)
                wav_writer.setsampwidth(sample_width)
                wav_writer.setnchannels(1)
                wav_writer.writeframes(raw_data)
                wav_data = wav_file.getvalue()
            finally:
                wav_writer.close()
        return wav_data

    def get_raw_data(self, convert_rate=None, convert_width=None):
        """
        Returns a byte string representing the raw frame data for the audio represented
        by the ``AudioData`` instance.
        """
        assert convert_rate is None or convert_rate > 0, \
            "Sample rate to convert to must be a positive integer"
        assert convert_width is None or (convert_width % 1 == 0 and 1 <= convert_width <= 4), \
            "Sample width to convert to must be between 1 and 4 inclusive"

        raw_data = self.frame_data

        # make sure unsigned 8-bit audio (which uses unsigned samples) is handled like higher sample width audio
        if self.sample_width == 1:
            raw_data = audioop.bias(raw_data, 1, -128)

        # resample audio at the desired rate if specified
        if convert_rate is not None and self.sample_rate != convert_rate:
            raw_data, _ = audioop.ratecv(
                raw_data, self.sample_width, 1, self.sample_rate, convert_rate, None
            )

        # convert samples to desired sample width if specified
        if convert_width is not None and self.sample_width != convert_width:
            raw_data = audioop.lin2lin(raw_data, self.sample_width, convert_width)

        # if the output is 8-bit audio with unsigned samples, convert the samples we've been treating as signed to unsigned
        if convert_width == 1:
            raw_data = audioop.bias(raw_data, 1, 128)

        return raw_data


class Alternative(TypedDict):
    transcript: str
    confidence: float


class Result(TypedDict):
    alternative: List[Alternative]
    final: bool


class GoogleResponse(TypedDict):
    result: List[Result]
    result_index: int


class UnknownValueError(Exception):
    """Raised when the speech is unintelligible."""
    pass


class RequestError(Exception):
    """Raised when the speech recognition operation failed."""
    pass


class Recognizer:
    """
    A speech recognizer instance that represents a collection of speech recognition functionality.
    """

    def __init__(self):
        """
        Creates a new ``Recognizer`` instance.
        """
        self.operation_timeout = 10  # seconds

    def record(self, source, duration=None, offset=None):
        """
        Records up to ``duration`` seconds of audio from ``source`` (an ``AudioSource`` instance)
        starting at ``offset`` (or at the beginning if not specified) into an ``AudioData`` instance,
        which it returns.

        If ``duration`` is not specified, then it will record until there is no more audio input.
        """
        assert isinstance(source, AudioSource), "Source must be an audio source"
        assert source.stream is not None, "Audio source must be entered before recording"

        frames = io.BytesIO()
        seconds_per_buffer = (source.CHUNK + 0.0) / source.SAMPLE_RATE
        elapsed_time = 0
        offset_time = 0
        offset_reached = False
        while True:  # loop for the total number of chunks needed
            if offset and not offset_reached:
                offset_time += seconds_per_buffer
                if offset_time > offset:
                    offset_reached = True

            buffer = source.stream.read(source.CHUNK)
            if len(buffer) == 0:
                break

            if offset_reached or not offset:
                elapsed_time += seconds_per_buffer
                if duration and elapsed_time > duration:
                    break

                frames.write(buffer)

        frame_data = frames.getvalue()
        frames.close()
        return AudioData(frame_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)

    def recognize_google(self, audio_data, key=None, language="en-US", show_all=False):
        """
        Performs speech recognition on ``audio_data`` (an ``AudioData`` instance),
        using the Google Speech Recognition API.

        The Google Speech Recognition API key is specified by ``key``. If not specified,
        it uses a generic key that works out of the box.

        The recognition language is determined by ``language``, an RFC5646 language tag
        like ``"en-US"`` (US English) or ``"fr-FR"`` (International French),
        defaulting to US English.

        Returns the most likely transcription if ``show_all`` is False (the default).
        Otherwise, returns the raw API response as a JSON dictionary.

        Raises a ``UnknownValueError`` exception if the speech is unintelligible.
        Raises a ``RequestError`` exception if the speech recognition operation failed.
        """
        assert isinstance(audio_data, AudioData), "``audio_data`` must be audio data"

        flac_data = audio_data.get_flac_data(
            convert_rate=None if audio_data.sample_rate >= 8000 else 8000,
            convert_width=2  # audio samples must be 16-bit
        )

        # Construct the request
        if key is None:
            key = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"  # Default API key
        
        url = "http://www.google.com/speech-api/v2/recognize?{}".format(urlencode({
            "client": "chromium",
            "lang": language,
            "key": key,
            "pFilter": "0",  # No profanity filter
        }))
        
        request = Request(
            url,
            data=flac_data,
            headers={"Content-Type": f"audio/x-flac; rate={audio_data.sample_rate}"}
        )

        try:
            response = urlopen(request, timeout=self.operation_timeout)
            response_text = response.read().decode("utf-8")
        except HTTPError as e:
            raise RequestError(f"recognition request failed: {e.reason}")
        except URLError as e:
            raise RequestError(f"recognition connection failed: {e.reason}")

        # Parse the response
        actual_result = None
        for line in response_text.split("\n"):
            if not line:
                continue
            
            result = json.loads(line).get("result", [])
            if len(result) != 0:
                if len(result[0].get("alternative", [])) == 0:
                    raise UnknownValueError()
                actual_result = result[0]
                break
        
        if actual_result is None:
            raise UnknownValueError()

        if show_all:
            return actual_result

        # Return the most likely transcription
        alternatives = actual_result["alternative"]
        if "confidence" in alternatives[0]:
            # Return alternative with highest confidence score
            best_hypothesis = max(alternatives, key=lambda alternative: alternative["confidence"])
        else:
            # When there is no confidence available, we arbitrarily choose the first hypothesis
            best_hypothesis = alternatives[0]
        
        if "transcript" not in best_hypothesis:
            raise UnknownValueError()
        
        return best_hypothesis["transcript"]