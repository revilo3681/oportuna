# Modelo de datos

PostgreSQL es la fuente de verdad. Las migraciones viven en `apps/api/migrations` y se aplican automáticamente en el arranque del contenedor.

## Entidades principales

### `opportunities`

Identidad y contenido:

- `id` (UUID), `slug` único, `title`, `summary`, `description`.
- `category` (`hackathons` | `eventos` | `formacion` | `startups`), `subcategory`.
- `tech_tags` (JSONB) y `tech_tags_text` (`|ai|ml|`) para filtros portables.
- `modality` (`online` | `presencial` | `hibrida` | `unknown`), `country`, `city`, `timezone`, `language`.
- `organizer`, `organizer_url`, `official_url`, `registration_url`, `canonical_url`.
- `edition_year`.

Fechas — **campos separados**:

- `event_start`, `event_end` (celebración).
- `registration_open_at`, `registration_deadline` (inscripción/solicitud).
- `submission_deadline` (entregas; Devpost usa este campo para el fin de envíos).
- `results_at`, `phases` (JSONB), `rolling` (convocatoria continua).
- `duration_minutes`, `prep_time_minutes`, `commitment_note`.

Condiciones:

- `cost_type`, `cost_amount`, `currency`.
- `prizes` (JSONB), `eligibility` (JSONB), `team_min`, `team_max`.

Estado y confianza:

- `lifecycle`, `registration_state`, `registration_state_source`.
- `verification_state`, `confidence_score`, `confidence_reasons`, `conflict_count`.
- `review_state`, `review_reason`, `published`, `published_at`.
- `quality_score` (orden base del catálogo).
- `last_checked_at`, `last_verified_at`, `last_changed_at`, `first_seen_at`.
- `search_text`, `is_demo`.

### `field_provenance`

Una fila por campo material y fuente:

- `opportunity_id`, `field`, `source_id`.
- `value` JSONB (`{"value": ...}`).
- `observed_at`, `method` (`ics`, `jsonld`, `devpost`, …).
- `confidence`, `is_official`, `note`.

Permite afirmaciones como “la fecha límite está confirmada por el organizador, pero el premio sigue pendiente”. La ficha muestra la última observación por campo.

### `opportunity_sources`

Un registro por vínculo oportunidad ↔ fuente:

- `source_url`, `external_id`, `retrieved_at`, `raw_excerpt`, `authority`.

`external_id` evita duplicados cuando la misma fuente republica el registro.

### `verification_checks`

Histórico de comprobaciones (`confirmed`, `reachable`, `unreachable`, `lead`) con estado HTTP y evidencia. Una comprobación de accesibilidad **no** cambia el estado de inscripción.

### `opportunity_changes`

Auditoría campo a campo:

- `field`, `old_value`, `new_value`, `source_id`, `actor` (`system` | `admin`), `reason`, `created_at`.

Se usa para explicar por qué una oportunidad pasó de abierta a cerrada.

### `duplicate_candidates`

Pares ambiguos:

- `left_id`, `right_id` (UUID ordenados), `score`, `reasons` (JSONB), `status`, `note`, `resolved_by`.

Nunca se fusionan automáticamente los casos dudosos.

### `sources`

Registro declarativo:

- `slug`, `name`, `kind`, `homepage_url`, `endpoint`, `region`, `languages`.
- `config` (JSONB): allowlist, límites, país por defecto, palabras excluidas.
- `authority`, `enabled`, `frequency_minutes`.
- `last_run_at`, `last_status`, `last_error`, `consecutive_failures`, `disabled_reason`.
- `access_notes`, `terms_url`.

### `users` y `profiles`

- `users`: email único, hash scrypt, rol (`user`/`admin`), estado de baja lógica.
- `profiles`: intereses, nivel, objetivos, país/ciudad, radio, modalidades, idiomas, disponibilidad, bloques de tiempo, presupuesto, elegibilidad, preferencias y `onboarded_at`.

El perfil es opcional y se puede vaciar sin eliminar la cuenta.

### `saved_opportunities`

Seguimiento por usuario: estado, notas, feedback de utilidad (`useful`), timestamps.

### `alerts` e `ingestion_runs`

- `alerts`: avisos de cierre, digest y cambios.
- `ingestion_runs`: métricas por fuente (encontradas, creadas, actualizadas, publicadas, revisión, errores, duración, coste, resumen).

### `assistant_queries`

Registro de preguntas, filtros interpretados y número de resultados. No se guarda contenido sensible.

---

## Reglas de fechas

1. Si la fuente no declara una fecha, el campo es `NULL` y la UI muestra “por confirmar/desconocida”.
2. `parse_date_range` rechaza rangos sin año explícito; no asume el año actual.
3. “Dec 28 – Jan 4, 2026” se interpreta como inicio en 2025 y fin en 2026.
4. Los plazos de solo fecha se guardan al final del día UTC.
5. `effective_deadline` elige el cierre más próximo entre inscripción y entregas para ordenar y avisar, pero la ficha muestra ambos.
6. `derive_lifecycle` combina fechas y estado declarado; una URL accesible no lo altera.

---

## Índices y búsqueda

- Índices por `slug`, `category`, `registration_deadline`, `published`, `review_state`, `verification_state`, `country`, `edition_year`.
- `search_text` normalizado (sin acentos) para búsqueda textual portable.
- `tech_tags_text` evita depender de operadores JSON específicos de Postgres.
- Cuando el volumen lo exija: `tsvector` + GIN y búsqueda semántica en una tabla de embeddings.

---

## Migraciones

```bash
cd apps/api
alembic revision --autogenerate -m "descripción"
alembic upgrade head
```

Reglas:

- No borrar columnas sin migración de datos.
- Mantener compatibilidad con SQLite en tests (usar tipos portables: `JSON` con variante JSONB, `Uuid`, `DateTime(timezone=True)`).
- Toda migración debe probarse con una base limpia (`docker compose down -v` + arranque).
