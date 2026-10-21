# Oportuna — Especificación funcional v1

## 1. Propósito

Oportuna es una capa de inteligencia sobre oportunidades tecnológicas. Descubre convocatorias en fuentes públicas, comprueba su fiabilidad, las organiza por relevancia personal y ayuda a decidir el siguiente paso. No inscribe, no paga y no promete resultados.

**Principio rector:** el usuario debe poder confiar en lo que ve sin creer en una etiqueta. La confianza se demuestra con procedencia, fechas y motivos.

---

## 2. Decisiones de diseño (cerradas)

| # | Decisión | Implementación |
| --- | --- | --- |
| 1 | Cobertura amplia con incertidumbre etiquetada | Se ingieren muchas fuentes; cada campo conserva su procedencia y su estado. Lo no confirmado se muestra como pendiente. |
| 2 | Publicación automática estricta + revisión humana para lo dudoso | `publication_decision()` exige verificación, confianza ≥ 0.70, fechas accionables, enlace oficial y comprobación reciente. El resto va a `needs_review`. |
| 3 | Perfil, disponibilidad y recomendaciones desde v1 | El onboarding pide intereses, modalidad y disponibilidad; el ranking usa tiempo, presupuesto y elegibilidad. |

---

## 3. Personas

- **Estudiante explorador**: poco tiempo, busca becas, talleres y hackathons accesibles; necesita filtros por coste, nivel y modalidad.
- **Profesional que cambia de rumbo**: busca fellowships, programas de investigación y comunidades; valora prestigio, idioma y compatibilidad horaria.
- **Founder / builder**: sigue aceleradoras, retos y competiciones; necesita premios, fechas y requisitos.
- **Administrador de datos**: mantiene la calidad, resuelve duplicados, revisa conflictos y desactiva fuentes rotas.

---

## 4. Flujos principales

### 4.1 Descubrimiento diario

1. El scheduler encola la ingesta según `OPORTUNA_INGEST_INTERVAL_MINUTES` (6 h por defecto).
2. Cada fuente se consulta con allowlist, límites y identificación.
3. Los registros se normalizan y se comparan contra el catálogo.
4. Se calcula confianza y se aplica la compuerta de publicación.
5. Lo verificado aparece en el catálogo; lo ambiguo en la cola de revisión.
6. El panel muestra nuevas oportunidades, cierres próximos y prioridad personal.

### 4.2 Primera visita

- Se ve el catálogo abierto y el panel general, sin registro.
- Se ofrece activar el radar con un perfil mínimo (intereses, modalidad, país, días disponibles).
- Se explica qué mejora con el perfil y qué no se pedirá.

### 4.3 Búsqueda

1. Texto libre + filtros combinables: categoría, tecnología, modalidad, país, idioma, coste, cierre en N días, incluir cerradas.
2. Se muestran facets con conteos, chips de filtros activos y paginación.
3. Cada resultado declara estado de verificación, plazo y fuente.
4. Los resultados no publicados no existen para el usuario público.

### 4.4 Ficha

Debe contener, como mínimo:

- Descripción y resumen (o declaración explícita de que la fuente no los publica).
- Fecha de evento y fecha límite de inscripción **separadas**; fechas de entregas y resultados si existen.
- Requisitos de edad, país, nivel, equipo e invitación.
- Premios y coste, con “por confirmar” cuando falten.
- Idioma, zona horaria, modalidad y duración.
- Organizador, enlace oficial y enlace de registro.
- Procedencia por campo, última comprobación y cambios.
- Siguientes pasos sugeridos.
- Nota de que la elegibilidad final la decide el organizador.

### 4.5 Guardar y seguir

Estados: guardada, siguiendo, postulada, aceptada, asistida, descartada. Feedback “me resultó útil” para mejorar el ranking.

### 4.6 Calendario

Vistas mes, semana, día y agenda. Incluye fechas límite y eventos de las oportunidades guardadas. Exportación `.ics`. Sin integraciones externas automáticas.

### 4.7 Asistente

- Entrada: pregunta libre.
- Parseo determinista de categoría, tecnología, modalidad, coste, país e idioma/horizonte.
- Consulta solo oportunidades publicadas.
- Respuesta con citas y enlace a la ficha y a la fuente.
- Si no hay coincidencias, lo dice; no inventa.
- Sin LLM por defecto; el modo es explícito (`uses_llm: false`).

### 4.8 Administración

- Alta de fuentes declarativas (`ics`, `rss`, `jsonld`, `devpost`, `github`).
- Ejecución manual, habilitar/deshabilitar, ver último error.
- Cola de revisión con motivos y señales de confianza.
- Aprobación, ocultación y corrección manual con auditoría.
- Resolución de duplicados: fusionar o marcar como distintos.
- Métricas de cobertura, frescura, confianza, errores y coste.
- Ningún resultado ambiguo se publica sin decisión humana.

---

## 5. Modelo de estados

### Ciclo de vida (oportunidad)

`open` · `rolling` · `closed` · `finished` · `cancelled` · `unknown`

Derivado de fechas y, cuando la fuente lo declara, de su propio estado. Nunca de que una URL cargue.

### Verificación

`verified` · `pending` · `conflict` · `closed`

### Revisión

`published` · `needs_review` · `approved` · `hidden`

`published` solo se asigna automáticamente si se superan todas las compuertas. `approved` es una decisión humana explícita y auditada.

### Inscripción

`open` · `closed` · `unknown`. Se separa del ciclo de vida. Solo se marca `open` si hay una fecha límite futura publicada o la fuente declara convocatoria continua.

---

## 6. Reglas de confianza

Señales:

1. Autoridad de la fuente (0–100).
2. Confirmación oficial o plataforma de referencia.
3. Recencia de la comprobación.
4. Coherencia de fechas (inicio ≤ fin; sin plazos absurdos).
5. Presencia de enlace de registro (no implica apertura).
6. Contradicciones entre fuentes.

La puntuación se acompaña siempre de motivos legibles. No existe “100 % confiable”.

Compuertas de publicación automática:

- Estado `verified`.
- Confianza ≥ `OPORTUNA_AUTO_PUBLISH_MIN_CONFIDENCE` (0.70).
- Fecha de celebración o plazo accionable.
- Enlace oficial.
- Comprobación en los últimos `OPORTUNA_AUTO_PUBLISH_MAX_AGE_DAYS` (21) días.
- Cero contradicciones abiertas.

Cumplir una compuerta no anula las demás.

---

## 7. Criterios de aceptación (v1)

- [x] El esquema distingue evento, inscripción, entregas y resultados; soporta rolling y fases.
- [x] Cada campo material conserva fuente, método, fecha de observación y confianza.
- [x] Una fuente nueva `ics`/`rss`/`jsonld` se añade sin cambios de código.
- [x] El 100 % de los registros ingeridos tiene enlace a su fuente.
- [x] Ninguna fecha inferida se presenta como confirmada.
- [x] La publicación automática exige validación estricta; lo ambiguo va a revisión.
- [x] La ficha muestra estado, confianza, motivos, fuente y última comprobación.
- [x] El catálogo filtra por categoría, tecnología, país, modalidad, coste, idioma y fecha.
- [x] El perfil se completa progresivamente y se puede vaciar.
- [x] El ranking explica cada recomendación y usa diversidad por categoría.
- [x] El calendario exporta `.ics` sin integraciones no autorizadas.
- [x] El asistente solo responde con datos publicados y cita fuentes.
- [x] El admin puede revisar, aprobar, ocultar, corregir y fusionar con auditoría.
- [x] Docker Compose levanta el stack completo en un entorno limpio.
- [x] El sistema funciona sin usuarios conectados (worker + scheduler).
- [ ] Cobertura equilibrada en al menos 3 regiones fuera de EE. UU./Europa con fuentes activas — **parcial**: hay señales de África, Asia y Oceanía, pero no una base regional estable.
- [ ] Búsqueda recursiva de organizadores — **pendiente** (fase 2 de descubrimiento).

---

## 8. No objetivos de la v1

- Inscripción automatizada, pagos o compromisos en nombre del usuario.
- Scraping que eluda protecciones o viole condiciones de acceso.
- Chatbot generativo libre sobre el catálogo.
- Matching de equipos y funciones sociales.
- Promesas de elegibilidad sin requisitos publicados.
- Cobertura “global completa” desde el día uno.

---

## 9. Preguntas abiertas

1. ¿Qué fuentes regionales priorizar para LatAm, Asia y África con acceso permitido?
2. ¿Qué umbral de confianza y qué ventana de re-comprobación usar para cada tipo de fuente?
3. ¿Cómo medir “utilidad” sin introducir sesgos de popularidad?
4. ¿Qué modelo de verificación humana escala mejor: por fuente o por categoría?
5. ¿Conviene enriquecer descripciones con un LLM? Si sí, con revisión humana y campos separados.
