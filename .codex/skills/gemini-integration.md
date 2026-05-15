---
name: gemini-integration
description: Google Gemini API integration for OCR (vision), chat LLM, and embeddings. Multi-model fallback (2.0-flash → 2.5-flash), free tier optimization, image preprocessing.
---

# Gemini Integration Patterns

## Models
| Model | Use Case | Free Tier |
|---|---|---|
| gemini-2.0-flash | Chat, OCR, Entity extraction | 1,500 req/day |
| gemini-2.5-flash | Fallback for OCR/chat | 1,500 req/day |
| text-embedding-004 | Embeddings | 100 batches/day |

## Client Setup
```python
from google import genai
from google.genai import types

class GeminiProvider:
    MODEL_PRIORITY = ["gemini-2.0-flash", "gemini-2.5-flash"]
    EMBED_MODEL = "text-embedding-004"
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
    
    async def generate(self, prompt: str, system: str = None, config: dict = None):
        for model in self.MODEL_PRIORITY:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=config.get("temperature", 0.2),
                        top_p=config.get("top_p", 0.6),
                        max_output_tokens=config.get("max_tokens", 2048)
                    )
                )
                return response.text
            except Exception as e:
                if "rate limit" in str(e).lower():
                    continue
                raise
        raise RuntimeError("Todos los modelos Gemini fallaron")
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding with free tier respect."""
        results = []
        for batch in self._batch(texts, size=100):  # 100 per batch (free limit)
            response = self.client.models.embed_content(
                model=self.EMBED_MODEL,
                contents=batch
            )
            results.extend([e.values for e in response.embeddings])
        return results
    
    def _batch(self, items, size=100):
        for i in range(0, len(items), size):
            yield items[i:i+size]
```

## Image Preprocessing
```python
from PIL import Image
import io

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DIMENSION = 3072

def preprocess_image(image_bytes: bytes) -> bytes:
    """Resize image if too large before sending to Gemini."""
    img = Image.open(io.BytesIO(image_bytes))
    
    # Resize if dimensions exceed max
    if max(img.size) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    # Compress if file size exceeds max
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    
    if output.tell() > MAX_IMAGE_SIZE:
        # Further compress as JPEG
        output = io.BytesIO()
        img = img.convert('RGB')
        img.save(output, format='JPEG', quality=85, optimize=True)
    
    return output.getvalue()
```

## Token Counting (approximate)
```python
def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 chars per token for Spanish/English."""
    return len(text) // 4
```

## Rate Limiting
```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, requests_per_minute: int = 15):
        self.rpm = requests_per_minute
        self.requests = []
    
    async def wait(self):
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        self.requests = [r for r in self.requests if r > cutoff]
        
        if len(self.requests) >= self.rpm:
            wait_time = 60 - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.requests.append(datetime.now())
```
