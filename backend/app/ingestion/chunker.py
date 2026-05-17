"""Text chunking strategies."""

import re


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[dict]:
    """
    Split text into overlapping chunks.
    
    Returns list of dicts with 'content' and 'index' keys.
    """
    if not text or not text.strip():
        return []
    
    # Normalize whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    
    chunks = []
    current_index = 0
    
    # Strategy: split by paragraphs first, then by sentences if needed
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += para + "\n"
        else:
            # Save current chunk
            if current_chunk.strip():
                chunks.append({
                    "content": current_chunk.strip(),
                    "index": current_index
                })
                current_index += 1
            
            # Handle paragraph larger than chunk_size
            if len(para) > chunk_size:
                # Split by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= chunk_size:
                        current_chunk += sent + " "
                    else:
                        if current_chunk.strip():
                            chunks.append({
                                "content": current_chunk.strip(),
                                "index": current_index
                            })
                            current_index += 1
                        # Start with overlap from previous chunk
                        words = current_chunk.split()
                        overlap_word_count = max(5, chunk_overlap // 10)
                        overlap_text = " ".join(words[-overlap_word_count:]) if len(words) > overlap_word_count else ""
                        current_chunk = overlap_text + " " + sent + " "
            else:
                current_chunk = para + "\n"
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            "content": current_chunk.strip(),
            "index": current_index
        })
    
    return chunks
