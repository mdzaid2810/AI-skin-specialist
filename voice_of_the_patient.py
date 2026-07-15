# Step1: Record audio from microphone

# dependencies: ffmpeg, portaudio, pyaudio (commands available in description)
import logging
import shutil
import warnings
from io import BytesIO
from pathlib import Path
import struct
import wave

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover - handled at runtime
    sr = None

from pydub import AudioSegment

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def record_audio(file_path, timeout=20, phrase_time_limit=None):
    """
    Simplified function to record audio from the microphone and save it as an MP3 file.
    
    Args:
    file_path (str): Path to save the recorded audio file.
    timeout (int): Maximum time to wait for a phrase to start (in seconds).
    phrase_time_lfimit (int): Maximum time for the phrase to be recorded (in seconds).
    """
    if sr is None:
        raise RuntimeError("speech_recognition is not available. Install speechrecognition and pyaudio to record microphone audio.")

    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        logging.info("Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        logging.info("Start speaking now...")
        
        # Record the audio
        audio_data = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        logging.info("Recording complete.")
        
        # Convert the recorded audio to an MP3 file
        wav_data = audio_data.get_wav_data()
        audio_segment = AudioSegment.from_wav(BytesIO(wav_data))
        audio_segment.export(file_path, format="mp3", bitrate="128k")
        
        logging.info(f"Audio saved to {file_path}")

audio_filepath="patient_voice_test.mp3"
#record_audio(audio_filepath, timeout=20, phrase_time_limit=10)


# Step2: Convert audio to text
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

def _fallback_transcribe_with_google(audio_filepath):
    if sr is None:
        raise RuntimeError("speech_recognition is not available. Install speechrecognition and pyaudio to use the fallback transcription path.")

    recognizer = sr.Recognizer()
    with sr.AudioFile(str(audio_filepath)) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio)


def _check_audio_quality(audio_filepath):
    filepath = Path(audio_filepath)
    suffix = filepath.suffix.lower()

    if suffix in {".wav", ".wave"}:
        try:
            with wave.open(str(filepath), "rb") as wf:
                if wf.getsampwidth() != 2:
                    return
                nframes = wf.getnframes()
                frames = wf.readframes(nframes)
                if not frames:
                    raise RuntimeError(
                        "The patient audio file is empty or invalid. "
                        "Please upload a clear voice recording."
                    )
                fmt = "<{}h".format(nframes * wf.getnchannels())
                samples = struct.unpack(fmt, frames)
                max_amp = max(abs(sample) for sample in samples)
                if max_amp < 500:
                    raise RuntimeError(
                        "The patient audio is too quiet or unclear for reliable transcription. "
                        "Please upload a clearer voice recording or use a better microphone input."
                    )
        except wave.Error:
            return
        return

    ffprobe_path = shutil.which("ffprobe") or shutil.which("avprobe")
    if not ffprobe_path:
        logging.warning(
            "FFprobe/avprobe not found; skipping audio quality check for non-WAV inputs."
        )
        return

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            audio_segment = AudioSegment.from_file(str(audio_filepath))
    except FileNotFoundError as fnf_error:
        logging.warning("FFmpeg not available for audio quality checks: %s", fnf_error)
        return
    except Exception as audio_error:
        logging.warning("Unable to perform audio quality check: %s", audio_error)
        return

    if audio_segment.dBFS == float("-inf") or audio_segment.dBFS < -40.0:
        raise RuntimeError(
            "The patient audio is too quiet or unclear for reliable transcription. "
            "Please upload a clearer voice recording or use a better microphone input."
        )


def transcribe_patient_voice(audio_filepath):
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("Missing GROQ_API_KEY in environment. Please set it in your .env or shell before running the app.")

    if not audio_filepath or not Path(audio_filepath).exists():
        raise ValueError("No patient audio file was found. Please record or upload your voice description.")
 
    _check_audio_quality(audio_filepath)
    client = Groq(api_key=groq_api_key)
    try:
        with open(audio_filepath, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model=os.environ.get("WHISPER_MODEL", "whisper-large-v3"),
            )
        return transcription.text
    except Exception as groq_error:
        logging.warning("Groq transcription failed: %s", groq_error)
        try:
            return _fallback_transcribe_with_google(audio_filepath)
        except Exception as google_error:
            raise RuntimeError(
                "Audio transcription failed using Groq and fallback Google Speech Recognition. "
                f"Groq error: {groq_error}. Fallback error: {google_error}."
            ) from google_error