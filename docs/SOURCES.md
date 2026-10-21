# Fuentes, acceso y política de expansión

## Principio

Oportuna solo consulta lo que la fuente permite consultar. No se eluden CAPTCHAs, muros de pago, límites de peticiones ni restricciones de `robots.txt`. Cuando una plataforma exige credenciales o un acuerdo, se documenta como pendiente en lugar de simular una integración.

Cada fuente declara:

- `endpoint` y `homepage_url` públicos.
- `allowed_domains`: dominios permitidos para esa fuente.
- `authority` (0–100): señal de reputación, no una verdad absoluta.
- `frequency_minutes`, `config` (límites, país por defecto, palabras excluidas).
- `access_notes` y `terms_url`.

---

## Fuentes activas (verificadas en esta implementación)

| Fuente | Tipo | Endpoint | Qué aporta | Autoridad | Frecuencia |
| --- | --- | --- | --- | --- | --- |
| Devpost | `devpost` | `https://devpost.com/api/hackathons?status[]=open&per_page=100` | Hackathons con temáticas, premios y fin de envíos | 85 | 6 h |
| PyTorch Foundation Events | `jsonld` | `https://pytorch.org/events/` | Conferencias, meetups y hackathons globales (JSON-LD schema.org) | 90 | 12 h |
| UC Berkeley Events | `ics` | `https://events.berkeley.edu/live/ical/events` | Charlas, seminarios y talleres tecnológicos | 80 | 12 h |
| MIT Calendar | `ics` | `https://calendar.mit.edu/calendar.ics` | Seminarios, conferencias y talleres | 82 | 12 h |
| Cornell Events | `ics` | `https://events.cornell.edu/calendar.ics` | Eventos tecnológicos y hackathons | 78 | 12 h |
| Stanford Events | `ics` | `https://events.stanford.edu/calendar.ics` | Charlas de IA, política tecnológica y talleres | 80 | 12 h |
| Opportunities For Africans | `rss` | `https://www.opportunitiesforafricans.com/feed/` | Becas, fellowships y programas (pistas) | 45 | 12 h |

### Particularidades por adaptador

**Devpost**

- `submission_period_dates` se interpreta como periodo de envíos: se guarda en `event_start`/`event_end` y `submission_deadline`.
- **No** se afirma que la inscripción esté abierta. `open_state` se usa como estado declarado de la convocatoria, y el enlace de envío se conserva como `registration_url` con nota.
- `prize_amount` viene con HTML; se limpia y se extrae importe y moneda.
- `invite_only` se registra como requisito, no como elegibilidad general.

**PyTorch Events**

- Se leen solo bloques `application/ld+json` con `@type: Event`; no se ejecuta JavaScript.
- `startDate`/`endDate` conservan su zona horaria original y se normalizan a UTC.
- `offers.price = 0` se interpreta como gratuito; si no hay precio, coste desconocido.
- `eventAttendanceMode` determina modalidad.

**Calendarios `.ics`**

- Se exige señal tecnológica **en el título** para evitar falsos positivos de descripciones genéricas (“data”, “technology”).
- Se excluyen palabras de ruido (building hours, naloxone, raffle, wellness, etc.).
- Si el `DTSTART` no tiene año o la fuente no lo publica, no se inventa.
- Una misma página de serie con fechas distintas se trata como eventos recurrentes, no como duplicados.
- Los eventos pasados se conservan como historial, no como abiertos.

**RSS**

- Es una pista, no una convocatoria confirmada (`confirmed=False`).
- Solo se aceptan entradas con señal tecnológica y verbo de oportunidad.
- Las fechas límite se extraen **solo** cuando el texto declara explícitamente “Application Deadline: …”.
- Nunca se publica automáticamente: entra en la cola de revisión.

**GitHub**

- Adaptador implementado pero **deshabilitado por defecto**.
- Los repositorios con `topic:hackathon` no son convocatorias. Se guardan como pistas y no se publican.
- La API de búsqueda sin token tiene límites estrictos.

---

## Fuentes pendientes (no integradas, con motivo)

| Plataforma | Estado | Motivo y siguiente paso |
| --- | --- | --- |
| MLH | Pendiente | No hay API pública documentada estable; la web es dinámica. Requiere revisar condiciones y acordar acceso, o un adaptador HTML frágil con revisión. |
| Luma | Pendiente | La API pública exige identificadores de calendario y credenciales/permiso; los calendarios privados no son accesibles. |
| Meetup | Pendiente | API con OAuth y condiciones específicas; el scraping de páginas no es aceptable. |
| Eventbrite | Pendiente | API v3 requiere token y permisos; el RSS público no cubre búsquedas. |
| Universidades de LatAm/Asia/África/Oceanía | Parcial | Hay señales (Uganda, Corea, Japón, Australia, África) vía PyTorch y RSS, pero no feeds institucionales estables verificados. Siguiente paso: validar `.ics`/JSON-LD por institución. |
| Organizadores recurrentes | Pendiente | La búsqueda recursiva (organizador → calendario → nuevas convocatorias) está diseñada pero no implementada en v1. |

No se presentan como integraciones lo que solo son candidatos.

---

## Añadir una fuente sin tocar código

1. Entra a `/admin` → **Fuentes** → **Registrar fuente**.
2. Elige tipo `ics`, `rss` o `jsonld` (los adaptadores genéricos).
3. Indica endpoint público, sitio, región, autoridad y condiciones de acceso.
4. Se crea **deshabilitada**. Verifica manualmente que el endpoint responde y que su uso es permitido.
5. Actívala y ejecútala. Revisa la cola de revisión y las métricas de la primera pasada.
6. Ajusta `config`: `lookahead_days`, `max_items`, `require_tech`, `default_country`, `exclude_keywords`, `allowed_domains`.

Ejemplo de configuración para un calendario:

```json
{
  "lookahead_days": 120,
  "max_items": 40,
  "require_tech": true,
  "default_country": "PE",
  "language": "es",
  "exclude_keywords": ["horario de atención", "reunión interna"]
}
```

---

## Política de expansión controlada

- **Allowlist** por fuente; una redirección fuera del dominio permitido se rechaza.
- **Rate limit** por dominio (1 req/s por defecto) y tamaño máximo de respuesta (8 MB).
- **robots.txt** respetado salvo APIs públicas documentadas (el adaptador lo declara explícitamente).
- **Reintentos** solo para 429/5xx, con backoff y `Retry-After` acotado.
- **Fallos**: 5 fallos consecutivos desactivan la fuente y dejan motivo visible en admin.
- **Coste**: cada ejecución registra `cost_usd`; hoy las fuentes son gratuitas, pero el campo está listo.
- **Procedencia**: el 100 % de los registros ingeridos enlaza la fuente y la fecha de consulta.

---

## Qué no se hará

- Rastrear páginas tras login, pagos o muros de autenticación.
- Resolver CAPTCHAs o imitar navegadores para eludir bloqueos.
- Publicar datos de fuentes que prohíben expresamente su uso.
- Inventar una integración “en camino” para completar una lista.
