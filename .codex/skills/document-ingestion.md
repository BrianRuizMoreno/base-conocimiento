---
name: document-ingestion
description: Document parsing for PDF, DOCX, MD, JSON, XML, images (Gemini OCR), audio/video (Whisper). Streaming for large files, smart chunking, no file size limits.
---

# Document Ingestion Patterns

## Parser Registry
```python
PARSERS = {
    "pdf":   parse_pdf,
    "docx":  parse_docx,
    "md":    parse_md,
    "json":  parse_json_streaming,
    "xml":   parse_xml,
    "image": parse_image_ocr,
    "audio": parse_audio_whisper,
    "video": parse_video_whisper,
}
```

## PDF (PyMuPDF)
```python
import fitz  # PyMuPDF

def parse_pdf(file_path: str) -> list[str]:
    pages = []
    with fitz.open(file_path) as doc:
        for page_num, page in enumerate(doc):
            text = page.get_text()
            pages.append(text)
    return pages
```

## DOCX (python-docx)
```python
from docx import Document

def parse_docx(file_path: str) -> list[str]:
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return paragraphs
```

## JSON (streaming with ijson)
```python
import ijson

def parse_json_streaming(file_path: str):
    """Generator: yields text chunks without loading entire file."""
    buffer = []
    buffer_size = 0
    with open(file_path, 'rb') as f:
        for prefix, event, value in ijson.parse(f):
            text = json.dumps({prefix: value})
            buffer.append(text)
            buffer_size += len(text)
            if buffer_size > 50000:  # 50KB flush
                yield "\n".join(buffer)
                buffer = []
                buffer_size = 0
    if buffer:
        yield "\n".join(buffer)
```

## XML (lxml)
```python
from lxml import etree

def parse_xml(file_path: str, mode="structured") -> str:
    tree = etree.parse(file_path)
    if mode == "structured":
        return _xml_to_text(tree.getroot(), depth=0)
    else:
        return " ".join(tree.itertext())

def _xml_to_text(elem, depth=0):
    indent = "  " * depth
    text = f"{indent}{elem.tag}: {elem.text.strip() if elem.text else ''}"
    for child in elem:
        text += "\n" + _xml_to_text(child, depth + 1)
    return text
```

## Image OCR (Gemini Flash with fallback)
```python
from google import genai
from google.genai import types

GEMINI_MODELS = ["gemini-2.0-flash", "gemini-2.5-flash"]

async def parse_image_ocr(image_path: str, api_key: str) -> str:
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    for model_name in GEMINI_MODELS:
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(image_bytes, "image/png"),
                    "Extrae TODO el texto visible en esta imagen. Incluye números, fechas, nombres. Sé exhaustivo."
                ],
                config=types.GenerateContentConfig(temperature=0.0)
            )
            return response.text
        except Exception:
            continue
    raise OCRFailedError("Todos los modelos Gemini fallaron")
```

## Audio/Video (faster-whisper local)
```python
from faster_whisper import WhisperModel
import subprocess

model = WhisperModel("base", device="cpu", compute_type="int8")

def parse_audio_whisper(file_path: str) -> str:
    segments, _ = model.transcribe(file_path, language="es")
    return " ".join([s.text for s in segments])

def parse_video_whisper(file_path: str) -> str:
    # Extract audio with ffmpeg
    audio_path = file_path + ".wav"
    subprocess.run([
        "ffmpeg", "-i", file_path, "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", audio_path, "-y"
    ], check=True, capture_output=True)
    return parse_audio_whisper(audio_path)
```

## Chunking Service (no file size limits)
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentChunker:
    def __init__(self, max_tokens=1500, overlap=200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def chunk_text(self, text: str) -> list[str]:
        return self.splitter.split_text(text)
    
    def chunk_stream(self, file_path: str, file_type: str):
        """Generator that yields chunks without loading entire file."""
        parser = PARSERS[file_type]
        if file_type in ("json", "csv"):
            for raw_text in parser(file_path):
                yield from self.chunk_text(raw_text)
        else:
            texts = parser(file_path)
            for text in texts:
                yield from self.chunk_text(text)
```

## Upload Pipeline
```python
async def upload_document(file: UploadFile, collection_id: UUID, db: AsyncSession):
    # 1. Save to disk
    # 2. Detect file type
    # 3. Parse + chunk (streaming)
    # 4. Deduplicate by hash
    # 5. Embed new chunks
    # 6. Store in pgvector
    # 7. Extract entities for graph
    # 8. Update document status = 'indexed'
    # 9. Log execution
```

## Progress Tracking
```python
class UploadProgress:
    """Tracks progress for large file uploads."""
    def __init__(self, file_id: UUID, total_chunks: int):
        self.file_id = file_id
        self.total = total_chunks
        self.processed = 0
    
    def increment(self):
        self.processed += 1
        # Emit via WebSocket or store in Redis/DB
        # Frontend polls GET /api/v1/documents/{id}/progress
```
