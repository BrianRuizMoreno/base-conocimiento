---
name: whisper-integration
description: Audio and video transcription using faster-whisper (local, no API cost). CPU-optimized, supports Spanish, handles long files via segmentation.
---

# Whisper Integration Patterns

## Model Selection
| Model | Size | Speed | Quality | VRAM Required |
|---|---|---|---|---|
| tiny | 39MB | fastest | acceptable | ~1GB |
| base | 74MB | fast | good | ~1GB |
| small | 244MB | moderate | better | ~2GB |
| medium | 769MB | slower | very good | ~5GB |
| large-v3 | 1550MB | slowest | best | ~10GB |

For your VPS (8GB RAM, no GPU): use **base** or **small** with CPU + `int8` quantization.

## Setup
```python
from faster_whisper import WhisperModel

# CPU-only, quantized for low RAM
model = WhisperModel(
    "base",  # or "small" if RAM allows
    device="cpu",
    compute_type="int8",  # reduces memory by ~50%
    cpu_threads=2  # your VPS has 2 cores
)
```

## Audio Transcription
```python
def transcribe_audio(file_path: str) -> str:
    segments, info = model.transcribe(
        file_path,
        language="es",
        task="transcribe",
        vad_filter=True,  # Voice Activity Detection removes silence
        vad_parameters=dict(min_silence_duration_ms=500)
    )
    return " ".join([segment.text for segment in segments])
```

## Video Transcription
```python
import subprocess
import os

def extract_audio(video_path: str) -> str:
    """Extract audio from video to WAV."""
    audio_path = video_path.rsplit('.', 1)[0] + '.wav'
    subprocess.run([
        'ffmpeg', '-i', video_path,
        '-vn',  # no video
        '-acodec', 'pcm_s16le',
        '-ar', '16000',  # 16kHz for Whisper
        '-ac', '1',       # mono
        audio_path,
        '-y'  # overwrite
    ], check=True, capture_output=True)
    return audio_path

def transcribe_video(video_path: str) -> str:
    audio_path = extract_audio(video_path)
    try:
        return transcribe_audio(audio_path)
    finally:
        os.remove(audio_path)  # cleanup temp audio
```

## Long File Handling
```python
from pydub import AudioSegment
import math

SEGMENT_MINUTES = 10

def transcribe_long_audio(file_path: str) -> str:
    """Split long audio into segments, transcribe each, concatenate."""
    audio = AudioSegment.from_file(file_path)
    duration_ms = len(audio)
    segment_ms = SEGMENT_MINUTES * 60 * 1000
    num_segments = math.ceil(duration_ms / segment_ms)
    
    transcriptions = []
    for i in range(num_segments):
        start = i * segment_ms
        end = min((i + 1) * segment_ms, duration_ms)
        segment = audio[start:end]
        segment_path = f"/tmp/segment_{i}.wav"
        segment.export(segment_path, format="wav")
        transcriptions.append(transcribe_audio(segment_path))
        os.remove(segment_path)
    
    return " ".join(transcriptions)
```

## Cost
**$0** — everything runs locally on CPU.
