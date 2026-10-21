# IA local (Ollama)

Oportuna usa tu propia IA, ejecutada en tu equipo con **Ollama**. No hay claves de API, no hay envío de preguntas a la nube y el catálogo no sale de la base de datos local.

## Modelos detectados

- **Chat:** `gemma4:12b-q4` (configurable).
- **Embeddings:** `nomic-embed-text:latest`.
- Alternativas instaladas: `gemma4:e4b-q4`, `gemma4:e2b-q4`.

El backend consulta `http://127.0.0.1:11434/api/tags` y elige el modelo configurado si existe. Si no, toma el primer modelo de chat disponible.

## Cómo responde

1. Interpreta la pregunta con reglas (categoría, tecnología, modalidad, precio, país, plazo).
2. Consulta el catálogo **publicado y abierto**.
3. Si la pregunta es vaga o hay pocos resultados, añade **búsqueda semántica** con embeddings locales.
4. Construye un contexto numerado con un máximo de 6 oportunidades: título, fechas, plazo, coste, requisitos, confianza, fuente y resumen. **No incluye datos no publicados ni HTML.**
5. Envía un prompt con reglas estrictas: solo contexto, citas `[n]`, nada de URLs, nada de inventar, no afirmar elegibilidad.
6. Renumera las citas para que coincidan con las tarjetas mostradas y descarta URLs generadas por el modelo.
7. Devuelve la respuesta, las oportunidades citadas y enlaces oficiales extraídos de la base de datos.

Si Ollama no está disponible, el endpoint devuelve una respuesta determinista con reglas y lo indica (`mode: rules`). Si el modelo falla a mitad, se usa `rules-fallback`.

## Configuración

```env
OPORTUNA_LLM_ENABLED=true
OPORTUNA_LLM_BASE_URL=http://127.0.0.1:11434
OPORTUNA_LLM_MODEL=gemma4:12b-q4
OPORTUNA_LLM_EMBED_MODEL=nomic-embed-text:latest
OPORTUNA_LLM_TIMEOUT_SECONDS=180
OPORTUNA_LLM_MAX_CONTEXT_ITEMS=6
```

Con Docker, la API necesita llegar al Ollama del host:

```env
OPORTUNA_LLM_BASE_URL=http://host.docker.internal:11434
```

El compose incluye `extra_hosts: host.docker.internal:host-gateway` para Linux. En macOS Docker Desktop suele resolverlo directamente.

## Privacidad y seguridad

- El contenido de las fichas se trata como **datos no confiables**. Se envuelve en `<oportunidad>` y el sistema ordena ignorar instrucciones embebidas.
- El modelo no recibe correos, perfiles ni tokens.
- El modelo no recibe URLs: los enlaces de la respuesta se construyen desde PostgreSQL.
- La respuesta se limita a 4.000 caracteres y 350 tokens de salida; `think` está desactivado para evitar respuestas vacías y latencia excesiva.
- Timeout de 180 s; si falla, se degrada a reglas.

## Rendimiento observado

- Chat con 6 oportunidades: **17–36 s** en `gemma4:12b-q4` (primer token tras cargar el modelo).
- Embeddings de ~100 oportunidades: se construyen una vez y se cachean en memoria hasta que cambie el catálogo (TTL 10 min).
- La UI muestra el tiempo transcurrido y el modelo usado.

## Limitaciones actuales

- Sin streaming token a token (se muestra progreso y tiempo).
- La calidad del español depende del modelo local.
- No hay evaluación automática de alucinaciones; el prompt y las citas reducen el riesgo, pero se recomienda una muestra manual.
- El índice semántico vive en memoria por proceso; con varias réplicas cada worker construye el suyo.
- La extracción estructurada de nuevas fuentes con IA (fechas/premios desde HTML) todavía no está implementada; la ingesta sigue siendo determinista.

## Probar

```bash
curl -s http://127.0.0.1:8000/api/assistant/status | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/api/assistant/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"¿Qué hackathons de IA online gratis puedo hacer este mes?","use_ai":true}' \
  | python3 -m json.tool
```
