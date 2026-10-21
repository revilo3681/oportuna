# Qué falta para que Oportuna funcione “de verdad”

Este documento responde a una pregunta concreta: **¿qué le falta al producto para operar como un servicio real, con datos suficientes y fiable?** Se separa lo técnico de lo que depende de terceros (permisos, acuerdos, infraestructura).

Estado de partida (v0.1.0): descubrimiento, verificación, deduplicación, perfil, ranking, calendario, asistente, administración y automatización implementados y probados con 7 fuentes reales.

---

## Resumen honesto

La aplicación ya **funciona de verdad** en un sentido: descubre oportunidades reales, las verifica, las publica solo si superan controles y permite personalizar y seguir. Lo que le falta para ser un producto en producción no es “más pantallas”, sino:

1. **Más cobertura real** (en especial Latinoamérica, Asia y África, y plataformas con permisos).
2. **Alertas que lleguen por email/push**, no solo dentro de la app.
3. **Infraestructura desplegada y observada** (dominio, TLS, backups, métricas).
4. **Cuentas y operación de admin en producción** (invitaciones, roles, recuperación).
5. **Búsqueda semántica y un asistente con LLM controlado** (opcional, con citas).
6. **Métricas de utilidad** y validación manual muestral.

---

## 1. Cobertura de fuentes (el mayor bloqueo real)

| Qué falta | Por qué bloquea | Esfuerzo |
| --- | --- | --- |
| MLH, Luma, Meetup, Eventbrite | No tienen API pública estable o exigen credenciales/permisos. Sin acuerdo o token no es legal ni estable integrarlas. | Medio (adaptador) + gestión de acceso |
| Universidades y comunidades de LatAm, Asia, África, Oceanía | Hay señales indirectas, pero pocos feeds `.ics`/JSON-LD institucionales verificados. | Medio (validación por fuente) |
| Organizadores recurrentes | No existe aún la búsqueda recursiva (organizador → calendario → nuevas convocatorias). | Alto |
| Fuentes en español y portugués | La cobertura está sesgada al inglés. | Medio |

**Qué necesitaría de ti:** acceso o aprobación a esas plataformas, y una lista corta de organizaciones regionales prioritarias para validar sus feeds.

---

## 2. Alertas fuera de la app

Hoy las alertas se generan y se guardan (`alerts`), pero no se envían.

| Qué falta | Detalle |
| --- | --- |
| Proveedor de email transaccional | Resend, Postmark, SES o SMTP. Sin esto no hay digest ni aviso de cierre. |
| Plantillas de digest y cierre | Declaradas en el producto; falta implementar el envío. |
| Push web / móvil | Requiere servicio de notificaciones y permisos del usuario. |
| Frecuencia configurable | Ya existe el modelo de preferencias; falta UI y worker de envío. |
| Baja y no saturación | Doble opt-in, límite diario y enlace de baja. |

**Qué necesitaría de ti:** cuenta de email transaccional (o SMTP) y decisión sobre si el primer canal es email o push.

---

## 3. Infraestructura de producción

| Qué falta | Detalle |
| --- | --- |
| Servidor y dominio | Un host (VPS, Fly, Render, AWS/ECS) y dominio con TLS. |
| Construcción de imágenes | Los Dockerfiles existen; el build no se completó en este equipo por un fallo del daemon. En CI/Docker Desktop sano debería construirse; verificarlo en CI. |
| CI/CD | GitHub Actions para tests, lint, build y despliegue. |
| Backups | `pg_dump` programado y prueba de restauración. |
| Observabilidad | OpenTelemetry + logs estructurados + Grafana/Loki (hoy hay logs y métricas internas). |
| Secretos | Gestor de secretos (no `.env` en el servidor). |
| Escalado | Worker/scheduler independientes; Redis gestionado para más de una réplica. |

**Qué necesitaría de ti:** presupuesto de hosting, dominio y decisión de proveedor. Con eso puedo dejar CI/CD y despliegue listos.

---

## 4. Cuentas y operación

| Qué falta | Detalle |
| --- | --- |
| Recuperación de contraseña | Hoy no hay envío de email de reseteo. Bloqueante para usuarios reales. |
| Verificación de email | Evita cuentas falsas y permite alertas. |
| Roles e invitaciones | Solo existe `user`/`admin`; falta invitar admins y auditoría de usuarios. |
| Términos y privacidad | Textos legales y consentimiento de datos. |
| Borrado con retención | Ya hay borrado de perfil/cuenta; falta política documentada de retención. |

**Qué necesitaría de ti:** decisiones legales (titular, país de tratamiento, política) y el proveedor de email del punto 2.

---

## 5. Inteligencia avanzada

| Qué falta | Detalle |
| --- | --- |
| Asistente con LLM en la nube | Ya existe IA local (Ollama + embeddings) con citas y fallback. Falta evaluación de alucinaciones, streaming y, si se desea, un proveedor en la nube. |
| Búsqueda semántica | Requiere embeddings y vectores; útil cuando el catálogo crezca. |
| Estimación de esfuerzo | Solo cuando la fuente publica duración/preparación. Un modelo requeriría validación humana. |
| Matching de equipos | Función social posterior; requiere moderación y privacidad. |

**Qué necesitaría de ti:** clave de modelo (si quieres LLM) y decisión de prioridad frente a cobertura.

---

## 6. Calidad y operación de datos

| Qué falta | Detalle |
| --- | --- |
| Búsqueda recursiva | Fase 2 de descubrimiento; hoy la expansión es por fuentes declarativas. |
| Detección automática de contradicciones | Hoy se detectan al actualizar; falta comparación cruzada explícita. |
| A/B testing de ranking | Pesos configurables; falta asignación de cohortes y métrica. |
| Feedback en el ranking | Se almacena “me resultó útil”; falta incorporarlo sin premiar popularidad. |
| Validación manual muestral | Proceso periódico de revisión para medir precisión real. |
| Coste por oportunidad útil | Métricas de ingesta sí; falta medir coste y utilidad por oportunidad. |

---

## 7. Lo que ya no falta (no te lo cobres como pendiente)

- Modelo de datos con fechas separadas, procedencia por campo e historial.
- Verificación explicable y compuerta estricta de publicación.
- Deduplicación conservadora y cola de revisión.
- Catálogo, filtros, ficha, calendario e ICS.
- Perfil progresivo y ranking personalizado con motivos.
- Admin con revisión, corrección auditada, duplicados y métricas.
- Worker y scheduler funcionando.

---

## Orden recomendado

1. **Cerrar la brecha de confianza** (hecho en v0.1.1): no afirmar inscripción abierta sin fuente que lo diga.
2. **Email transaccional + recuperación de contraseña + verificación de email** (desbloquea alertas y usuarios reales).
3. **CI/CD + despliegue + backups** (desbloquea operar sin mí).
4. **Cobertura regional y plataformas con permisos** (el verdadero valor diferencial).
5. **Búsqueda recursiva de organizadores**.
6. **Búsqueda semántica y LLM controlado**.
7. **Métricas de utilidad y A/B testing**.

---

## Qué necesito de ti para seguir

Marca lo que quieras y lo abordo:

- [ ] Proveedor de email (Resend / Postmark / SMTP propio).
- [ ] Dominio y hosting (o “usa X”).
- [ ] Aprobación/acceso a MLH, Luma, Meetup o Eventbrite.
- [ ] Lista de organizaciones regionales prioritarias (LatAm, Asia, África, Oceanía).
- [ ] Documentos legales (términos, privacidad) o autorización para redactar borradores.
- [ ] Clave de LLM para el asistente (opcional).
- [ ] Repetir la construcción de Docker en un entorno con Docker saludable o CI.

Sin estas piezas puedo implementar todo el código, pero no puedo “activar” correos, permisos ni servidores por mi cuenta sin tu autorización.
