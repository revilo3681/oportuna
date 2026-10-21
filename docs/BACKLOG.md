# Backlog y estado real por épica

> Estado a fecha de la v0.1. “Hecho” significa implementado y probado, no solo diseñado.

| # | Épica | Estado | Qué queda |
| --- | --- | --- | --- |
| 1 | Modelo de datos y esquema base | ✅ Hecho | Tipos portables, procedencia por campo, fechas separadas, historial, migración inicial. |
| 2 | Motor de descubrimiento multifuente | 🟡 Parcial | 7 fuentes reales y fuentes declarativas. Falta búsqueda recursiva de organizadores y más plataformas. |
| 3 | Verificación, deduplicación y confianza | ✅ Hecho | Estados, confianza explicable, dedup conservadora, cola de revisión, procedencia y auditoría. |
| 4 | Catálogo, búsqueda y fichas | ✅ Hecho | Búsqueda textual, filtros combinables, facets, ficha completa, enlaces oficiales y exportación. |
| 5 | Perfil de usuario y disponibilidad | ✅ Hecho | Onboarding < 2 min, perfil progresivo, borrado de perfil/cuenta, distinción asistir/preparar. |
| 6 | Ranking y recomendaciones | 🟡 Parcial | Pesos, motivos, diversidad y elegibilidad. Falta A/B testing y feedback agregado en el ranking. |
| 7 | Automatización y tareas programadas | ✅ Hecho | Worker, scheduler, reverificación, alertas, métricas y política de fallos. |
| 8 | Panel de administración | ✅ Hecho | Fuentes, revisión, correcciones auditadas, duplicados, métricas y auditoría. |
| 9 | Arquitectura e infraestructura | ✅ Hecho | Compose con 7 servicios, migraciones automáticas, healthchecks, nginx. |
| 10 | Expansión global y multilingüe | 🟡 Parcial | Señales en África, Asia y Oceanía vía PyTorch/RSS. Faltan feeds institucionales estables por región. |
| 11 | Inteligencia avanzada | 🟡 Parcial | Asistente con IA local y citas, relacionadas, seguimiento. Faltan estimación de esfuerzo y matching de equipos. |
| 12 | Métricas de producto y calidad | 🟡 Parcial | Métricas internas de cobertura/frescura/errores/coste. Faltan analytics de utilidad y validación manual muestral. |

---

## Épica 1 — Modelo de datos

Hecho:

- Entidad `Opportunity` con categoría, subcategoría, etiquetas, modalidad y ciclo de vida.
- `event_start/end`, `registration_deadline`, `submission_deadline`, `results_at`, `phases`, `rolling`.
- `field_provenance` por campo; `opportunity_changes`; `verification_checks`.
- Usuarios, perfiles, fuentes, alertas, guardadas, métricas de ingesta.
- Migración Alembic inicial.

Siguiente:

- Tabla de embeddings y búsqueda semántica cuando el volumen lo justifique.
- Versionado de `phases` con estructuras tipadas.

## Épica 2 — Descubrimiento

Hecho:

- Adaptadores `devpost`, `jsonld`, `ics`, `rss`, `github`.
- Registro declarativo de fuentes; alta desde admin sin código para `ics/rss/jsonld`.
- Allowlist, robots, rate limit, límites de tamaño, reintentos y desactivación por fallos.
- Procedencia del 100 % de los registros.

Siguiente:

1. Búsqueda recursiva: detectar organizador → extraer enlaces a calendarios → proponer fuente → validar y activar con revisión humana.
2. Integraciones con permisos: MLH, Luma, Meetup y Eventbrite (ver `SOURCES.md`).
3. Detección de cambios de estructura en fuentes y tests con fixtures reales.
4. Deduplicación incremental más eficiente que comparar contra candidatos por tokens.

## Épica 3 — Verificación y confianza

Hecho:

- Confianza con señales observables y motivos.
- Estados de verificación y compuertas de publicación.
- Dedup por URL, nombre, organizador, fechas, ubicación y descripción.
- Series recurrentes con la misma URL no se fusionan.
- Cola de duplicados; fusión manual auditada.
- Una URL accesible no reabre una convocatoria.

Siguiente:

- Detección automática de contradicciones entre fuentes (hoy se marcan al actualizar).
- Panel de resolución de conflictos con comparación lado a lado.
- Reglas específicas por tipo de fuente para fechas de inscripción.

## Épica 4 — Catálogo y fichas

Hecho:

- Catálogo con q, categoría, tecnología, modalidad, país, idioma, coste, días y estado.
- Ficha con descripción, fechas, requisitos, premios, idioma, organizador, enlaces, fuente y última comprobación.
- Procedencia por campo, historial y siguientes pasos.
- ICS individual.

Siguiente:

- Búsqueda semántica opcional.
- Exportar/importar colecciones.
- Comparador de oportunidades.

## Épica 5 — Perfil

Hecho:

- Onboarding mínimo; ampliación progresiva en un `<details>`.
- Disponibilidad por días/franjas y bloques de tiempo.
- Edad, estudiante, idiomas, presupuesto, formato.
- Borrado de perfil y cuenta.

Siguiente:

- Onboarding guiado de 3 pasos en móvil.
- Zona horaria explícita por franja.
- Importar disponibilidad desde calendario (con autorización).

## Épica 6 — Ranking

Hecho:

- Pesos 30/25/20/15/10 configurables.
- Motivos por tarjeta.
- Diversidad por categoría y organizador.
- Elegibilidad con veredictos y advertencias.
- Feedback de utilidad almacenado.

Siguiente:

- A/B testing con cohortes y métrica de utilidad.
- Incorporar feedback agregado sin premiar popularidad.
- Ajustar la estimación de tiempo cuando la fuente no publica duración (hoy no se inventa).

## Épica 7 — Automatización

Hecho:

- Scheduler y worker separados.
- Ingesta cada 6 h, reverificación cada hora, alertas cada 6 h, digest diario.
- Reintentos y desactivación de fuentes.
- Métricas de ejecución y coste.

Siguiente:

- Reverificación adaptativa por cercanía de plazo (hoy ventana fija de 7 días).
- Alertas por email/push (hoy solo se almacenan).
- Cola con prioridades y límites por fuente.

## Épica 8 — Administración

Hecho:

- Resumen de calidad, fuentes, revisión, duplicados, auditoría.
- Aprobar/ocultar con nota.
- Corrección de campos desde la consola con auditoría (`PATCH /api/admin/opportunities/{id}`).
- Alta de fuentes.
- Ejecución manual.

Siguiente:

- Corrección de fechas de evento y premios desde un formulario más rico.
- Comparación visual de procedencia en conflictos.
- Historial de decisiones por administrador.

## Épica 9 — Infraestructura

Hecho:

- Compose con db, redis, api, worker, scheduler, web y nginx.
- Migraciones y seed automáticos.
- Healthchecks.
- Dockerfiles multi-stage; web standalone.

Siguiente:

- Kubernetes/ECS y despliegue con TLS.
- OpenTelemetry + Grafana/Loki.
- Backups automatizados y pruebas de restauración.

## Épica 10 — Expansión global

Hecho:

- Fuentes globales y señales en Uganda, Finlandia, Corea, Japón, Australia y África.
- Campos de país, idioma y región.

Siguiente:

1. Validar feeds `.ics`/JSON-LD de universidades y comunidades en LatAm, Asia, África y Oceanía.
2. Extracción multilingüe (hoy heurísticas ES/EN).
3. Detección de organizadores recurrentes.
4. Métricas de cobertura por región e idioma (admin ya las muestra; falta el objetivo).

## Épica 11 — Inteligencia avanzada

Hecho:

- Asistente con IA local (Ollama + embeddings) con citas, fallback determinista y negativa a inventar.
- Oportunidades relacionadas.
- Seguimiento guardada → postulada → aceptada.
- Feedback de utilidad.

Siguiente:

- Estimación de esfuerzo por oportunidad solo con datos verificables.
- Asistente con LLM opcional, con citas obligatorias y sin acceso a datos no publicados.
- Matching de equipos y funciones sociales.

## Épica 12 — Métricas de producto

Hecho:

- Cobertura (región, país, idioma, categoría).
- Frescura, cola de revisión, conflictos, duplicados, publicadas obsoletas, coste.
- Métricas de ingesta por fuente.

Siguiente:

- Dashboard de exactitud con muestreo manual.
- Medición de utilidad (guardados, postulaciones, retorno) con privacidad.
- Informe de coste por oportunidad útil y verificada.

---

## Prioridades recomendadas

1. **Cobertura regional real** (Épica 10) para no sesgar el catálogo.
2. **Recursión de organizadores** (Épica 2) para descubrir convocatorias nuevas sin depender de una lista fija.
3. **Feedback en ranking** (Épica 6) con control de sesgo.
4. **Alertas externas** (Épica 7).
5. **Observabilidad** (Épica 9) antes de escalar fuentes.

## Reglas que no se negocian

- Sin datos de demostración presentados como reales.
- Sin fechas inferidas como confirmadas.
- Sin publicación automática de lo ambiguo.
- Sin inscripciones, pagos o compromisos en nombre del usuario.
- Sin elusión de protecciones de acceso.
