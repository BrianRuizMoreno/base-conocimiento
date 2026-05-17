# Log de Ejecucion - Fase 2: Ingesta Completa de Documentos

**Fecha inicio:** 2026-05-16  
**Fecha completada:** 2026-05-16  
**Estado:** Completada

---

## Tareas completadas

- [x] 2.1 OCR de imagenes (.jpg, .png, .webp) con Gemini 2.0 Flash
- [x] 2.2 Extraer imagenes incrustadas de PDF (PyMuPDF)
- [x] 2.3 Extraer imagenes de DOCX (python-docx relaciones)
- [x] 2.4 Transcripcion de audio/video (.mp3, .mp4, .wav, .ogg) con faster-whisper + ffmpeg
- [x] 2.5 Servir imagenes estaticas (endpoint GET /api/v1/data/images/)
- [x] 2.6 Particionado a 20MB para archivos grandes (split_large_file)
- [x] 2.7 Indexar imagenes en vector store (metadata con image_paths en chunks)

---

## Archivos modificados/creados

### Backend

| Archivo | Cambios |
|---|---|
| `app/ingestion/parser.py` | **Reescrito** — parsers para PDF, DOCX, MD, TXT, JSON, XML, imagen (OCR Gemini), audio (Whisper), video (ffmpeg→audio→Whisper). Funciones `parse_pdf`, `parse_docx` ahora extraen imagenes incrustadas y las guardan en `/data/images/`. Funcion `split_large_file` para particionar archivos >20MB. |
| `app/ingestion/pipeline.py` | **Reescrito** — maneja archivos grandes (particionado), extrae imagenes del parser, guarda `image_paths` en metadata de chunks, loguea progreso detallado. |
| `app/api/documents.py` | **Reescrito** — mas tipos MIME soportados (webp, gif, bmp, tiff, wav, ogg, flac, m4a, avi, mkv, mov, wmv, flv, webm). Nuevo endpoint `POST /documents/{id}/reindex` para re-procesar. Endpoint `GET /data/images/{collection_id}/{document_id}/{image_name}` para servir imagenes extraidas. Delete ahora elimina tambien las imagenes extraidas. |
| `app/rag/engine.py` | Actualizado — busca `image_paths` en metadata de chunks recuperados y construye URLs publicas en `related_media` de la respuesta. |

### Frontend

| Archivo | Cambios |
|---|---|
| `src/pages/Chat.tsx` | Actualizado — renderiza imagenes relacionadas como thumbnails clickeables cuando la respuesta incluye `related_media`. Badge del modelo usado en cada respuesta. |

---

## Funcionalidades implementadas

### OCR de Imagenes
- Soporta .jpg, .jpeg, .png, .webp, .gif, .bmp, .tiff
- Usa Gemini 2.0 Flash con prompt "Extrae TODO el texto visible en esta imagen"
- Imagenes se redimensionan si exceden 3072px
- Compresion JPEG si exceden 5MB
- Fallback a mensaje informativo si Gemini no esta configurado

### Extraccion de Imagenes de Documentos
- **PDF**: PyMuPDF extrae todas las imagenes incrustadas por pagina
- **DOCX**: python-docx extrae imagenes de las relaciones del documento
- Imagenes guardadas en `/data/images/{collection_id}/{document_id}/`
- Referencias almacenadas en metadata del primer chunk del documento

### Transcripcion de Audio/Video
- **Audio**: faster-whisper local con modelo "base" (configurable)
- **Video**: ffmpeg extrae audio a WAV 16kHz mono → Whisper transcribe
- Soporta .mp3, .wav, .ogg, .flac, .m4a, .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm

### Particionado de Archivos Grandes
- Umbral: 20MB
- Archivos de texto se dividen en partes ~iguales respetando saltos de linea
- Archivos binarios (PDF, DOCX) se procesan como unidad
- Archivos temporales se limpian automaticamente

### Servicio de Imagenes
- Endpoint publico: `GET /api/v1/data/images/{collection_id}/{document_id}/{image_name}`
- Content-Type detectado por extension
- Requiere autenticacion (PIN)

### Retorno de Imagenes en Chat
- Cuando un chunk recuperado tiene `image_paths` en metadata
- El engine construye URLs y las incluye en `related_media`
- Frontend renderiza thumbnails clickeables que abren la imagen original

---

## Notas tecnicas

- La funcion `parse_file()` ahora retorna un `dict` en vez de un `str` para soportar multiples salidas (texto + imagenes + metadata)
- El `Document.metadata_` ahora incluye: `images_extracted`, `image_paths`, `parts_processed`, `ocr_used`, `source_type`
- Las imagenes extraidas de un documento se asocian al **primer chunk** de ese documento mediante `image_paths` en metadata
- El endpoint de reindex (`POST /documents/{id}/reindex`) permite re-procesar un documento despues de cambiar configuracion (ej: agregar API key de Gemini para OCR)

---

## Dependencias requeridas (ya en requirements.txt)

- `Pillow` (PIL) — redimension de imagenes para OCR
- `faster-whisper` — transcripcion de audio
- `ffmpeg` (sistema) — extraccion de audio de video
- `PyMuPDF` (fitz) — extraccion de texto e imagenes de PDF
- `python-docx` — extraccion de texto e imagenes de DOCX

---

## Proxima fase

Fase 3: Chat RAG Conversacional Avanzado  
- Historial de conversaciones multi-sesion
- Web search toggle (Tavily)
- Eliminar/modificar fuentes de informacion
