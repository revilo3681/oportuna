# Runbook operativo

## Servicios

| Servicio | Responsabilidad | Depende de |
| --- | --- | --- |
| `db` | PostgreSQL 16, fuente de verdad | — |
| `redis` | Cola de arq y resultados de trabajos | — |
| `api` | FastAPI, migraciones y seed al arrancar | db, redis |
| `worker` | Ingesta, reverificación y alertas | api, redis |
| `scheduler` | Encola ingesta, verificación, alertas y digest | api, redis |
| `web` | Next.js | api |
| `nginx` | Proxy `/` y `/api` | web, api |

## Arranque y parada

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=120
docker compose down          # conserva volúmenes
docker compose down -v       # BORRA base de datos y Redis (solo desarrollo)
```

El `entrypoint.sh` de la API espera a la base, aplica `alembic upgrade head`, ejecuta el seed idempotente y arranca uvicorn.

## Comprobaciones de salud

```bash
curl -s http://localhost:8080/api/health
curl -s http://localhost:8080/api/ready
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/
docker compose exec worker arq --check oportuna.worker.WorkerSettings  # opcional
```

En admin (`/admin`) revisa:

- **Frescura**: horas desde la última comprobación.
- **Fuentes con fallos** y errores recientes.
- **Cola de revisión**, conflictos y duplicados abiertos.
- **Publicadas obsoletas** (> 21 días sin comprobación).

## Ingesta manual

```bash
make ingest
# o dentro del contenedor:
docker compose exec api python -m oportuna.cli ingest
docker compose exec api python -m oportuna.cli ingest --slug devpost
docker compose exec api python -m oportuna.cli sources
docker compose exec api python -m oportuna.cli stats
```

La ingesta también se puede disparar desde `/admin` → Fuentes → **Ejecutar**. Requiere Redis disponible.

## Añadir o desactivar una fuente

- Alta: `/admin` → Fuentes → Registrar fuente. Se crea deshabilitada.
- Comprueba el endpoint y las condiciones antes de activarla.
- Desactivar: botón **Deshabilitar**. No borra datos históricos.
- Tras 5 fallos consecutivos, la fuente se desactiva automáticamente con motivo visible.

## Fallos frecuentes

### La API no arranca: base inaccesible

```bash
docker compose logs db
docker compose exec db pg_isready -U oportuna -d oportuna
```

El entrypoint reintenta 30 veces. Si la base se corrompió en desarrollo, `docker compose down -v` y vuelve a levantar (destructivo).

### “La cola de trabajos no está disponible (Redis)”

El botón **Ejecutar** del admin devuelve 503 si Redis no responde. Comprueba:

```bash
docker compose ps redis
docker compose exec redis redis-cli ping
```

La API pública sigue funcionando; solo se pierde el encolado. Ejecuta la ingesta por CLI mientras se resuelve.

### Una fuente devuelve errores

1. Admin → Fuentes → Detalles: revisa `last_error` y la configuración.
2. Prueba el endpoint manualmente (respeta condiciones y límites).
3. Ajusta `frequency_minutes`, `allowed_domains` o `max_items`.
4. Si cambió la estructura, actualiza el adaptador y añade un test con una muestra.
5. Reactiva y ejecuta; verifica la cola de revisión.

### Datos obsoletos en el catálogo

- El worker `verify_due_job` revisa oportunidades con cierre en 7 días.
- Para una revisión manual, ejecuta una ingesta de la fuente y revisa `last_checked_at`.
- Una comprobación de accesibilidad no reabre una convocatoria. Si hay duda, oculta la ficha desde admin hasta confirmar.

### Duplicados

- Admin → Duplicados: fusionar conserva el registro con mayor `quality_score`, mueve fuentes y procedencia, y audita la decisión.
- “Son distintas” cierra el par sin tocar los registros.
- Los duplicados exactos se fusionan en ingesta; nunca dos ediciones.

## Migraciones

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic current
docker compose exec api alembic revision --autogenerate -m "cambio"
```

Antes de migrar en producción: backup y prueba en una copia. No ejecutes `create_all` en producción; las tablas las gobierna Alembic.

## Backup programado

```bash
# Manual
./scripts/backup.sh ./backups

# Cron diario a las 03:15 (ejemplo)
15 3 * * * cd /ruta/a/oportuna && ./scripts/backup.sh ./backups >> ./backups/backup.log 2>&1
```

El script usa `pg_dump -Fc`, aborta si el backup está vacío y conserva 14 días por defecto (`BACKUP_RETENTION_DAYS`). Guarda los backups fuera del volumen de Docker y prueba la restauración periódicamente.

## Backup y restauración

```bash
# Backup
docker compose exec -T db pg_dump -U oportuna -d oportuna -Fc > oportuna-$(date +%F).dump

# Restaurar en una base vacía
docker compose exec -T db pg_restore -U oportuna -d oportuna --clean --if-exists < oportuna-2026-10-20.dump
```

Los datos personales (usuarios, perfiles, guardadas) deben cifrarse en reposo a nivel de infraestructura y retenerse el mínimo necesario.

## Rotación de secretos

1. Genera `OPORTUNA_JWT_SECRET` nuevo (≥ 32 bytes aleatorios).
2. Actualiza `.env` y reinicia API, worker y scheduler.
3. Las sesiones existentes quedan invalidadas (comportamiento esperado).
4. Rota la contraseña de admin y actualiza `OPORTUNA_SEED_ADMIN_PASSWORD` o cámbiala desde la base.

## Despliegue

- Compose está pensado para desarrollo y una instancia única. Para producción: gestionar secretos fuera del repo, TLS en el proxy, backups automáticos, límites de recursos y logs centralizados.
- El frontend usa `output: standalone`. La API se sirve detrás de nginx con `/api`.
- Variables críticas: `OPORTUNA_DATABASE_URL`, `OPORTUNA_REDIS_URL`, `OPORTUNA_JWT_SECRET`, `OPORTUNA_PUBLIC_SITE_URL`, `OPORTUNA_ENVIRONMENT=production`.
- El arranque falla si `environment=production` y el secreto JWT es el de desarrollo.

## Métricas a vigilar

- Tiempo desde la última comprobación por fuente.
- Tasa de error y fallos consecutivos por fuente.
- Proporción de registros publicados vs. revisión.
- Duplicados abiertos y conflictos.
- Cobertura por región, país, idioma y categoría.
- Coste por ejecución (hoy 0; preparado para APIs de pago).
- Uso: guardados, postulaciones y feedback de utilidad.

## Contacto y escalado

- Errores de datos: `hello@oportuna.dev` con enlace a la ficha y fuente.
- Fuente que prohíbe el acceso: desactivar de inmediato y documentar en `docs/SOURCES.md`.
- Incidente de seguridad: rotar JWT, revisar logs de la API, notificar según corresponda.
