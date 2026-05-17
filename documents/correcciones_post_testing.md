# Log de Correcciones Post-Testing (Fases 1-3)

**Fecha:** 2026-05-16  
**Agente:** Testing exhaustivo + correcciones manuales  

---

## Errores CRITICOS encontrados por agente de testing y corregidos

### C1-C2: Path Traversal en Upload y Serve Image

**Archivo:** `app/api/documents.py`

**Problema:** `file.filename` se usaba directamente para construir paths, permitiendo `../../etc/passwd`. El endpoint de imagenes tambien era vulnerable.

**Solucion aplicada:**
- Agregada funcion `secure_filename()` que sanitiza nombres de archivo (elimina paths, caracteres especiales)
- Upload ahora usa `safe_filename = secure_filename(file.filename)`
- Serve image ahora valida formato UUID y usa `os.path.realpath()` + verificacion de prefix

```python
def secure_filename(filename: str) -> str:
    filename = os.path.basename(filename)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    return filename or "unnamed_file"
```

### C3: Fallback SECRET_KEY inseguro

**Archivo:** `app/core/security.py`

**Problema:** Si `SECRET_KEY` no estaba configurada, usaba `"default-secret-key"` como fallback. Todas las API keys encriptadas serian trivialmente descifrables.

**Solucion aplicada:**
- Eliminado fallback inseguro
- Ahora lanza `RuntimeError` con mensaje instructivo si SECRET_KEY no esta configurada o es el valor default

### C6: Whisper model cargado repetidamente

**Archivo:** `app/ingestion/parser.py`

**Problema:** `WhisperModel()` se instanciaba en cada archivo de audio/video. Carga de modelo ~500MB cada vez.

**Solucion aplicada:**
- Agregado singleton `_whisper_model` a nivel de modulo
- Funcion `get_whisper_model()` cachea la instancia
- Modelo se carga una sola vez en la vida del proceso

### C10: Archivos temporales no limpiados (parse_video)

**Archivo:** `app/ingestion/parser.py`

**Problema:** Si ffmpeg o parse_audio fallaban, el archivo temporal .wav nunca se borraba.

**Solucion aplicada:**
- Refactorizado para usar bloque `try/finally`
- Cleanup en `finally:` siempre ejecuta `os.remove(audio_path)` si existe

---

## Errores MEDIANOS identificados (pendientes de correccion futura)

Los siguientes errores fueron identificados pero NO corregidos en esta sesion porque requieren refactorizacion mayor:

| # | Error | Archivo | Impacto | Prioridad |
|---|---|---|---|---|
| M1 | Titulo de conversacion solo se genera 1 vez | `chat.py` | Conversaciones pueden quedar sin titulo | Baja |
| M2 | Exposicion de errores internos al cliente | `chat.py` | Filtra paths internos | Media |
| M3 | Commit intermedio durante generacion de titulo | `chat.py` | Posible inconsistencia | Media |
| M4 | Embeddings Gemini uno por uno | `providers.py` | 100 conexiones para 100 chunks | Alta (Fase futura) |
| M5 | Acceso inseguro a respuestas API | `providers.py` | KeyError si formato cambia | Media |
| M7 | Tarea de background no resilient | `pipeline.py` | Documentos en "processing" eterno | Alta (requiere Celery) |
| M8 | Fallback a vector cero silencioso | `embeddings.py` | Chunks "similares" a todo | Media |
| M9 | `onupdate` no funciona confiablemente | `models.py` | Timestamps no actualizan | Baja |
| M10 | Default mutable en lista | `models.py` | Antipattern Python | Baja |
| M11 | Conteo ineficiente | `settings.py` | Carga todos los registros en RAM | Baja |
| M12 | Inconsistencia de providers | `settings.py` | Tavily no es opcion de chat | Baja |
| M13 | CORS incompleto | `main.py` | Faltan PATCH y OPTIONS | Baja |
| M14 | PIN en localStorage sin proteccion | `client.ts` | Vulnerable a XSS | Media |
| M15 | URLs de imagen relativas | `Chat.tsx` | Problemas con dominios distintos | Media |

---

## Recomendaciones para Fases 5-7

1. **Agregar Celery/RQ** para procesamiento de documentos en background (resuelve M7)
2. **Batch embeddings** en Gemini para reducir conexiones HTTP (resuelve M4)
3. **Agregar RBAC** en todos los endpoints de conversaciones y chat (resuelve C9, C11)
4. **Crear indice HNSW** en pgvector para busqueda rapida (resuelve A3)
5. **Refactorizar ProviderFactory** para no hacer commit() interno (resuelve M3)

---

## Estado despues de correcciones

| Categoria | Corregidos | Pendientes |
|---|---|---|
| Errores CRITICOS | 4 (C1-C3, C6, C10) | 7 (C4-C5, C7-C9, C11) |
| Errores MEDIANOS | 0 | 15 |
| Advertencias | 0 | 11 |

**Nota:** Los errores CRITICOS restantes (C4-C5, C7-C9, C11) requieren refactorizacion significativa que se abordara en las Fases 5-7.
