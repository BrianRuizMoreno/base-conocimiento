"""Document parsers for various file formats including images, audio, video."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Tuple
import logging
import os
import shutil

from app.core.config import settings

logger = logging.getLogger(__name__)

# Image extraction directories
IMAGES_DIR = os.path.join(settings.UPLOAD_DIR, "images")

# Whisper model singleton cache
_whisper_model = None

def get_whisper_model():
    """Get or create cached Whisper model instance."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        model_size = settings.WHISPER_MODEL or "base"
        device = settings.WHISPER_DEVICE or "cpu"
        logger.info(f"Loading Whisper model ({model_size}, {device})...")
        _whisper_model = WhisperModel(model_size, device=device, compute_type="int8")
        logger.info("Whisper model loaded and cached.")
    return _whisper_model


def ensure_images_dir(collection_id: str, document_id: str) -> str:
    """Create and return path for extracted images."""
    img_dir = os.path.join(IMAGES_DIR, str(collection_id), str(document_id))
    os.makedirs(img_dir, exist_ok=True)
    return img_dir


async def parse_file(file_path: str, file_type: str, collection_id: str = "", document_id: str = "") -> dict:
    """Parse a file and return extracted text and metadata.
    
    Returns dict with:
        - text: extracted text content
        - images: list of extracted image paths (if any)
        - metadata: additional parsing info
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    
    result = {"text": "", "images": [], "metadata": {}}
    
    if file_type == 'pdf' or ext == '.pdf':
        result = parse_pdf(file_path, collection_id, document_id)
    elif file_type == 'docx' or ext == '.docx':
        result = parse_docx(file_path, collection_id, document_id)
    elif file_type in ('md', 'txt') or ext in ('.md', '.txt', '.csv', '.py', '.js', '.ts', '.html', '.css'):
        result["text"] = parse_text(file_path)
    elif file_type == 'json' or ext == '.json':
        result["text"] = parse_json(file_path)
    elif file_type == 'xml' or ext in ('.xml', '.xlsx'):
        result["text"] = parse_xml(file_path)
    elif file_type == 'image' or ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'):
        result = await parse_image(file_path, collection_id, document_id)
    elif file_type == 'audio' or ext in ('.mp3', '.wav', '.ogg', '.m4a', '.flac', '.wma'):
        result["text"] = parse_audio(file_path)
        result["metadata"]["source_type"] = "audio"
    elif file_type == 'video' or ext in ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'):
        result["text"] = parse_video(file_path)
        result["metadata"]["source_type"] = "video"
    else:
        # Fallback: try to read as text
        try:
            result["text"] = parse_text(file_path)
        except Exception:
            result["text"] = ""
    
    return result


def parse_pdf(path: str, collection_id: str = "", document_id: str = "") -> dict:
    """Extract text and images from PDF using PyMuPDF."""
    import fitz
    
    text_parts = []
    images = []
    
    with fitz.open(path) as doc:
        for page_num, page in enumerate(doc):
            # Extract text
            text_parts.append(page.get_text())
            
            # Extract images
            if collection_id and document_id:
                img_list = page.get_images(full=True)
                for img_index, img in enumerate(img_list, start=1):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    img_dir = ensure_images_dir(collection_id, document_id)
                    img_filename = f"page_{page_num + 1}_img_{img_index}.{image_ext}"
                    img_path = os.path.join(img_dir, img_filename)
                    
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    images.append(img_path)
    
    return {
        "text": "\n".join(text_parts),
        "images": images,
        "metadata": {"total_pages": len(doc), "images_extracted": len(images)}
    }


def parse_docx(path: str, collection_id: str = "", document_id: str = "") -> dict:
    """Extract text and images from Word document."""
    from docx import Document
    from docx.oxml.ns import qn
    
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    
    # Extract images
    images = []
    if collection_id and document_id:
        img_dir = ensure_images_dir(collection_id, document_id)
        
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                image = rel.target_part
                image_bytes = image.blob
                # Determine extension from content type
                content_type = image.content_type
                ext = content_type.split('/')[-1] if '/' in content_type else 'png'
                if ext == 'jpeg':
                    ext = 'jpg'
                
                img_filename = f"image_{len(images) + 1}.{ext}"
                img_path = os.path.join(img_dir, img_filename)
                
                with open(img_path, "wb") as f:
                    f.write(image_bytes)
                images.append(img_path)
    
    return {
        "text": "\n".join(paragraphs),
        "images": images,
        "metadata": {"images_extracted": len(images)}
    }


def parse_text(path: str) -> str:
    """Read plain text file."""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def parse_json(path: str) -> str:
    """Extract text from JSON by serializing."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return json.dumps(data, ensure_ascii=False, indent=2)


def parse_xml(path: str) -> str:
    """Extract text from XML."""
    tree = ET.parse(path)
    texts = []
    for elem in tree.iter():
        if elem.text and elem.text.strip():
            texts.append(elem.text.strip())
    return "\n".join(texts)


async def parse_image(path: str, collection_id: str = "", document_id: str = "") -> dict:
    """Extract text from image using Gemini OCR."""
    import base64
    import httpx
    
    # Copy image to collection images dir
    images = []
    if collection_id and document_id:
        img_dir = ensure_images_dir(collection_id, document_id)
        ext = Path(path).suffix
        dest_path = os.path.join(img_dir, f"original{ext}")
        shutil.copy2(path, dest_path)
        images.append(dest_path)
    
    # Try OCR with Gemini if key available
    text = ""
    if settings.GEMINI_API_KEY:
        try:
            with open(path, "rb") as f:
                image_bytes = f.read()
            
            # Resize if too large
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes))
            
            # Resize if dimensions exceed max
            max_dim = 3072
            if max(img.size) > max_dim:
                ratio = max_dim / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            
            # Compress if file size exceeds 5MB
            output = io.BytesIO()
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.save(output, format='JPEG', quality=85, optimize=True)
            image_data = output.getvalue()
            
            # Encode to base64
            b64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Call Gemini for OCR
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}",
                    json={
                        "contents": [{
                            "parts": [
                                {"text": "Extrae TODO el texto visible en esta imagen. Si es un documento, tabla o grafico, transcríbelo fielmente. Responde SOLO con el texto extraído, sin comentarios adicionales."},
                                {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
                            ]
                        }],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": 4096
                        }
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    text = "".join([p.get("text", "") for p in parts])
            
        except Exception as e:
            logger.warning(f"OCR failed for {path}: {e}")
            text = "[Imagen sin texto extraible]"
    else:
        text = "[Imagen - OCR no disponible, configure una API key de Gemini]"
    
    return {
        "text": text,
        "images": images,
        "metadata": {"source_type": "image", "ocr_used": bool(text and settings.GEMINI_API_KEY)}
    }


def parse_audio(path: str) -> str:
    """Transcribe audio using faster-whisper."""
    try:
        model = get_whisper_model()
        
        logger.info(f"Transcribing audio with faster-whisper...")
        segments, info = model.transcribe(path, beam_size=5, language="es")
        texts = [segment.text for segment in segments]
        
        logger.info(f"Audio transcription completed. Language: {info.language}, Duration: {info.duration:.2f}s")
        return "\n".join(texts)
    
    except ImportError:
        logger.warning("faster-whisper not installed. Install with: pip install faster-whisper")
        return "[Audio - transcripcion no disponible: instale faster-whisper]"
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        return f"[Error en transcripcion de audio: {str(e)}]"


def parse_video(path: str) -> str:
    """Extract audio from video and transcribe using faster-whisper."""
    import tempfile
    
    audio_path = None
    try:
        # Extract audio using ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_path = tmp.name
        
        import subprocess
        cmd = [
            "ffmpeg", "-i", path, "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", "-y", audio_path
        ]
        
        logger.info(f"Extracting audio from video: {path}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg failed: {result.stderr}")
            return f"[Error extrayendo audio del video: {result.stderr[:200]}]"
        
        # Transcribe extracted audio
        text = parse_audio(audio_path)
        return text
    
    except FileNotFoundError:
        logger.warning("ffmpeg not found. Install with: apt install ffmpeg")
        return "[Video - ffmpeg no encontrado. Instale ffmpeg para procesar videos]"
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        return f"[Error procesando video: {str(e)}]"
    finally:
        # Cleanup temp file
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup temp file {audio_path}: {cleanup_err}")


def split_large_file(file_path: str, max_size_mb: int = 20) -> List[str]:
    """Split a large file into smaller chunks for processing.
    
    For text files: splits by lines.
    For binary files (PDF, DOCX): returns original path (handled by parser).
    """
    max_size = max_size_mb * 1024 * 1024
    file_size = os.path.getsize(file_path)
    
    if file_size <= max_size:
        return [file_path]
    
    ext = Path(file_path).suffix.lower()
    
    # For text-based files, split by content
    if ext in ('.txt', '.md', '.csv', '.json', '.xml', '.html', '.css', '.py', '.js', '.ts'):
        parts = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Split into chunks of roughly equal size
        total_chars = len(content)
        num_parts = (file_size // max_size) + 1
        chunk_size = total_chars // num_parts
        
        for i in range(num_parts):
            start = i * chunk_size
            end = start + chunk_size if i < num_parts - 1 else total_chars
            
            # Try to break at a newline
            if i < num_parts - 1 and end < total_chars:
                next_newline = content.find('\n', end)
                if next_newline != -1 and next_newline - end < 1000:
                    end = next_newline + 1
            
            chunk_content = content[start:end]
            
            # Save to temp file
            part_path = f"{file_path}.part{i + 1}{ext}"
            with open(part_path, 'w', encoding='utf-8') as f:
                f.write(chunk_content)
            parts.append(part_path)
        
        logger.info(f"Split large text file ({file_size} bytes) into {len(parts)} parts")
        return parts
    
    # For binary files, return as-is (parser handles internally)
    logger.info(f"Large binary file ({file_size} bytes) - processing as single file")
    return [file_path]
