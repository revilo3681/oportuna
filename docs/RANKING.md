# Ranking y personalización

## Objetivo

Ordenar por lo que realmente le sirve a una persona, no por popularidad ni por novedad. Cada recomendación debe poder explicarse en una frase.

## Fórmula

```text
score = 100 × (
    afinidad        × 0.30 +
    disponibilidad  × 0.25 +
    elegibilidad    × 0.20 +
    fiabilidad      × 0.15 +
    valor           × 0.10
)
```

Los pesos viven en `DEFAULT_WEIGHTS` (`apps/api/oportuna/domain/ranking.py`) y se pueden cambiar para experimentos. La confianza **no** es solo un criterio de orden: actúa antes, como compuerta de publicación.

### Afinidad (30 %)

- Coincidencia entre intereses declarados y `tech_tags`/categoría: 70 %.
- Coincidencia con objetivos (`aprender`, `crear`, `competir`, `premios`, `networking`, `carrera`): 20 %.
- Nivel declarado frente al nivel requerido: 10 %.
- Sin perfil: valor neutro (0.5). El panel muestra “Destacadas”, no “Para ti”.

### Disponibilidad (25 %)

- Urgencia del plazo (50 %): cierra esta semana (0.92), próximos 30 días (1.0), lejano (0.85), desconocido (0.62), cerrado (0.05).
- Modalidad compatible (15 %): si el perfil declara presencial y la oportunidad es online, no se penaliza; al contrario sí.
- Encaje de tiempo (20 %): `duración + preparación` frente al bloque máximo declarado. Si no hay duración publicada, no se inventa: se usa un valor neutro y se muestra “duración por confirmar”.
- Presupuesto (15 %): gratuito si el perfil pide gratis; “por confirmar” no se trata como gratis.

### Elegibilidad (20 %)

| Veredicto | Puntuación | Cuándo |
| --- | --- | --- |
| `eligible` | 1.0 | Todos los requisitos declarados se contrastaron y se cumplen. |
| `likely` | 0.8 | Se cumple lo comprobado, pero faltan datos del perfil. |
| `unknown` | 0.55 | La fuente no publica requisitos o no hay perfil. |
| `ineligible` | 0.05 | Un requisito publicado no se cumple. |

Nunca se muestra “eres elegible” si faltan requisitos. La ficha lo repite: la decisión final es del organizador.

### Fiabilidad (15 %)

Es la `confidence_score` descrita en la metodología: autoridad, confirmación, recencia, coherencia, enlace y contradicciones. Una oportunidad atractiva pero dudosa no asciende por su atractivo.

### Valor (10 %)

Base por categoría (formación 0.78, hackathons/startups 0.72, eventos 0.62), más premios publicados, coste gratuito, certificado declarado y posibilidad de equipo. No se prometen resultados.

---

## Diversidad

Después de ordenar:

- Máximo 2 tarjetas por categoría en la selección inicial.
- Máximo 2 por organizador.
- El resto se rellena con los mejores puntuados.

Esto evita que veinte hackathons de IA ocupen todo el panel cuando una beca o una charla encajan mejor.

---

## Motivos explicables

Cada tarjeta recibe hasta 5 motivos calculados:

- “Te interesa IA, hackathons”.
- “El plazo de participación termina pronto”.
- “Cabe en tu tiempo disponible”.
- “Posiblemente elegible; revisa los requisitos”.
- “Fuente verificada · confianza 84 %”.
- “Participación gratuita”.

Los motivos salen de datos; no son frases generadas.

---

## Ejemplo

Perfil: IA, principiante, online, sábados, bloques de 2–3 h, gratis.

| Oportunidad | Afinidad | Disponibilidad | Elegibilidad | Fiabilidad | Valor | Score |
| --- | --- | --- | --- | --- | --- | --- |
| Hackathon online de IA, 48 h, gratis, cierra en 5 días | 1.00 | 0.55 (no cabe en 3 h) | 0.55 | 0.90 | 0.92 | **78** |
| Webinar de IA de 1 h, gratis, cierra en 3 días | 1.00 | 0.98 | 0.55 | 0.88 | 0.70 | **84** |
| Bootcamp presencial de 5 días, 500 € | 0.90 | 0.20 | 0.55 | 0.85 | 0.78 | **61** |

El orden no dice que el hackathon sea peor: dice que no cabe en el tiempo declarado. La ficha permite guardarlo para más adelante.

---

## Feedback y experimentación

- El usuario puede marcar “me resultó útil” al guardar o seguir. Se almacena en `saved_opportunities.useful`.
- **Pendiente**: incorporar ese feedback al ranking de forma agregada y con control de sesgo. Hoy no altera los pesos.
- **Pendiente**: A/B testing de pesos con asignación de cohortes y métrica de utilidad. La estructura de pesos ya es configurable.
- La diversidad y la compuerta de confianza deben mantenerse en cualquier experimento.

---

## Límites

- La disponibilidad horaria se evalúa por día y franja; no hay calendario detallado ni zonas horarias por franja.
- La duración y la preparación solo se usan si la fuente las publica; el sistema no las estima.
- La elegibilidad depende de requisitos estructurados; descripciones legales complejas requieren revisión humana.
- El ranking no usa popularidad de terceros para evitar premiar ruido.
