"""Product taxonomy: categories, technologies, modalities and classification heuristics."""

from __future__ import annotations

import re
import unicodedata

CATEGORIES: dict[str, dict] = {
    "hackathons": {
        "label": "Hackathons",
        "tagline": "Competir, construir y ganar premios",
        "description": "Hackathons, datathons, competiciones de programación, CTF, concursos de IA, retos de empresas y desafíos open source.",
        "subcategories": [
            "hackathon",
            "datathon",
            "ctf",
            "concurso-ia",
            "reto-empresa",
            "open-source",
            "programacion-competitiva",
        ],
    },
    "eventos": {
        "label": "Eventos y comunidades",
        "tagline": "Charlas, talleres y demos",
        "description": "Conferencias, charlas, webinars, talleres, meetups, ferias, eventos universitarios, demos y networking.",
        "subcategories": ["conferencia", "meetup", "webinar", "taller", "feria", "demo", "universitario"],
    },
    "formacion": {
        "label": "Becas y programas",
        "tagline": "Aprendizaje y financiación",
        "description": "Becas, cursos gratuitos, bootcamps, fellowships, programas de investigación, estancias y certificaciones.",
        "subcategories": ["beca", "curso", "bootcamp", "fellowship", "investigacion", "certificacion"],
    },
    "startups": {
        "label": "Startups y carrera",
        "tagline": "Aceleradoras, retos e innovación",
        "description": "Aceleradoras, incubadoras, grants, programas para founders, prácticas, mentorías y programas para desarrolladores.",
        "subcategories": ["aceleradora", "incubadora", "grant", "founder", "practica", "mentoria", "voluntariado"],
    },
}

CATEGORY_KEYS = list(CATEGORIES.keys())

TECH_TAGS: dict[str, dict] = {
    "ai": {"label": "IA", "patterns": [r"\bai\b", r"artificial intelligence", r"inteligencia artificial", r"genai", r"generative"]},
    "ml": {"label": "Machine Learning", "patterns": [r"machine learning", r"\bml\b", r"deep learning", r"aprendizaje automatico"]},
    "agents": {"label": "Agentes de IA", "patterns": [r"agents?\b", r"agentes?", r"llm", r"large language models?"]},
    "robotics": {"label": "Robótica", "patterns": [r"robot", r"robotic", r"autonomous systems"]},
    "web": {"label": "Desarrollo web", "patterns": [r"\bweb\b", r"frontend", r"backend", r"full[- ]stack", r"javascript", r"react", r"next\.?js"]},
    "cloud": {"label": "Cloud", "patterns": [r"cloud", r"aws", r"azure", r"google cloud", r"serverless", r"kubernetes?"]},
    "devops": {"label": "DevOps", "patterns": [r"devops", r"platform engineering", r"infrastructure", r"infraestructura"]},
    "security": {"label": "Ciberseguridad", "patterns": [r"cyber", r"security", r"seguridad", r"ctf", r"hacking", r"privacy", r"privacidad"]},
    "data": {"label": "Datos", "patterns": [r"\bdata\b", r"datos", r"analytics", r"big data", r"data science", r"sql"]},
    "blockchain": {"label": "Blockchain", "patterns": [r"blockchain", r"web3", r"ethereum", r"solana", r"smart contracts?"]},
    "gamedev": {"label": "Videojuegos", "patterns": [r"game dev", r"gamedev", r"videojuegos?", r"unity", r"godot", r"esports"]},
    "oss": {"label": "Open source", "patterns": [r"open[- ]source", r"open source", r"foss", r"github"]},
    "mobile": {"label": "Móvil", "patterns": [r"mobile", r"android", r"ios", r"flutter", r"react native"]},
    "quantum": {"label": "Computación cuántica", "patterns": [r"quantum", r"cuantic"]},
    "iot": {"label": "IoT y hardware", "patterns": [r"\biot\b", r"hardware", r"embedded", r"arduino", r"raspberry"]},
    "xr": {"label": "AR / VR", "patterns": [r"\bvr\b", r"\bar\b", r"augmented reality", r"virtual reality", r"metaverse"]},
    "product": {"label": "Producto", "patterns": [r"product management", r"producto", r"\bux\b", r"design thinking"]},
    "climate": {"label": "Climatech", "patterns": [r"climate", r"clima", r"sustainability", r"sostenibilidad", r"\bgreen\b"]},
    "health": {"label": "Healthtech", "patterns": [r"health", r"salud", r"medtech", r"biotech"]},
}

MODALITIES = {
    "online": "Online",
    "presencial": "Presencial",
    "hibrida": "Híbrida",
    "unknown": "Por confirmar",
}

COST_TYPES = {"free": "Gratis", "paid": "De pago", "unknown": "Por confirmar"}

LIFECYCLES = {
    "open": "Inscripción abierta",
    "closed": "Inscripción cerrada",
    "cancelled": "Cancelado",
    "finished": "Finalizado",
    "rolling": "Convocatoria continua",
    "unknown": "Estado por confirmar",
}

VERIFICATION_STATES = {
    "verified": "Verificado",
    "pending": "Pendiente de verificar",
    "conflict": "Información contradictoria",
    "closed": "Cerrado o finalizado",
}

REVIEW_STATES = {
    "published": "Publicado",
    "needs_review": "En revisión",
    "approved": "Aprobado manualmente",
    "hidden": "Oculto",
}

LEVELS = {"principiante": "Principiante", "intermedio": "Intermedio", "avanzado": "Avanzado"}

GOALS = {
    "aprender": "Aprender",
    "crear": "Crear proyectos",
    "competir": "Competir",
    "premios": "Ganar premios",
    "networking": "Hacer networking",
    "carrera": "Oportunidades profesionales",
}

TIME_BUCKETS = {
    "15m": "15 minutos",
    "1h": "1 hora",
    "2-3h": "2–3 horas",
    "half-day": "Medio día",
    "multi-day": "Varios días",
}

BUDGETS = {"free": "Gratis", "transport": "Transporte asumible", "paid": "De pago", "any": "Cualquier precio"}

LANGUAGES = {
    "es": "Español", "en": "Inglés", "pt": "Portugués", "fr": "Francés", "de": "Alemán",
    "it": "Italiano", "nl": "Neerlandés", "pl": "Polaco", "tr": "Turco", "ru": "Ruso",
    "ar": "Árabe", "hi": "Hindi", "ja": "Japonés", "ko": "Coreano", "zh": "Chino",
    "id": "Indonesio", "vi": "Vietnamita", "th": "Tailandés", "sw": "Suajili", "uk": "Ucraniano",
}



COUNTRY_NAMES = {
    "AR": "Argentina", "AU": "Australia", "AT": "Austria", "BE": "Bélgica", "BO": "Bolivia",
    "BR": "Brasil", "CA": "Canadá", "CL": "Chile", "CN": "China", "CO": "Colombia",
    "CR": "Costa Rica", "CU": "Cuba", "CZ": "Chequia", "DE": "Alemania", "DK": "Dinamarca",
    "EC": "Ecuador", "EG": "Egipto", "ES": "España", "FI": "Finlandia", "FR": "Francia",
    "GB": "Reino Unido", "GH": "Ghana", "GR": "Grecia", "GT": "Guatemala", "HK": "Hong Kong",
    "HU": "Hungría", "ID": "Indonesia", "IE": "Irlanda", "IL": "Israel", "IN": "India",
    "IT": "Italia", "JP": "Japón", "KE": "Kenia", "KR": "Corea del Sur", "MA": "Marruecos",
    "MX": "México", "MY": "Malasia", "NG": "Nigeria", "NL": "Países Bajos", "NO": "Noruega",
    "NZ": "Nueva Zelanda", "PE": "Perú", "PH": "Filipinas", "PK": "Pakistán", "PL": "Polonia",
    "PT": "Portugal", "PY": "Paraguay", "RO": "Rumanía", "RS": "Serbia", "RU": "Rusia",
    "SA": "Arabia Saudí", "SE": "Suecia", "SG": "Singapur", "SV": "El Salvador", "TH": "Tailandia",
    "TR": "Turquía", "TW": "Taiwán", "UA": "Ucrania", "US": "Estados Unidos", "UY": "Uruguay",
    "VE": "Venezuela", "VN": "Vietnam", "ZA": "Sudáfrica",
}

REGIONS = {
    "global": "Global",
    "latam": "Latinoamérica",
    "europa": "Europa",
    "norteamerica": "Norteamérica",
    "asia": "Asia",
    "africa": "África",
    "oceania": "Oceanía",
}

TECH_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    tag: [re.compile(p, re.IGNORECASE) for p in info["patterns"]]
    for tag, info in TECH_TAGS.items()
}

CATEGORY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "hackathons": [re.compile(p, re.IGNORECASE) for p in [
        r"hackathon", r"hackaton", r"hack-a-thon", r"datathon", r"data ?jam",
        r"ctf\b", r"capture the flag", r"coding challenge", r"code challenge",
        r"competition", r"competencia", r"challenge", r"reto\b", r"concurs", r"contest",
        r"game jam", r"open source", r"bounty",
    ]],
    "formacion": [re.compile(p, re.IGNORECASE) for p in [
        r"scholarship", r"beca", r"fellowship", r"grant", r"bootcamp", r"course",
        r"curso", r"certification", r"certificaci", r"research program", r"internship",
        r"mentorship", r"residency", r"estancia",
    ]],
    "startups": [re.compile(p, re.IGNORECASE) for p in [
        r"accelerator", r"aceleradora", r"incubator", r"incubadora", r"founder",
        r"startup", r"entrepreneur", r"emprend", r"venture", r"pitch",
    ]],
    "eventos": [re.compile(p, re.IGNORECASE) for p in [
        r"conference", r"conferencia", r"summit", r"meetup", r"webinar", r"workshop",
        r"taller", r"talk", r"charla", r"demo day", r"tech fest", r"symposium",
        r"congress", r"congreso", r"devfest", r"hack day", r"expo", r"fair", r"feria",
    ]],
}

STRICT_TECH_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bai\b", r"artificial intelligence", r"inteligencia artificial", r"machine learning",
    r"deep learning", r"\bllms?\b", r"genai", r"generative ai", r"data science",
    r"big data", r"analytics", r"cyber", r"\bctf\b", r"hacking", r"software",
    r"developer", r"programming", r"programaci[oó]n", r"\bcoding\b", r"computer science",
    r"robotics?", r"rob[oó]tica", r"\bcloud\b", r"devops", r"kubernetes", r"serverless",
    r"blockchain", r"web3", r"quantum", r"open[- ]source", r"hackathon", r"datathon",
    r"startup", r"venture", r"\bapi\b", r"frontend", r"backend", r"full[- ]stack",
    r"algorithm", r"ciberseguridad", r"datos", r"tecnolog[ií]a",
]]

CALENDAR_CATEGORY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "hackathons": [re.compile(p, re.IGNORECASE) for p in [
        r"hackathon", r"hackaton", r"datathon", r"data ?jam", r"\bctf\b",
        r"capture the flag", r"game jam", r"coding (challenge|competition)",
        r"programming (challenge|competition)", r"hack day", r"open source sprint",
        r"bounty", r"robotics competition", r"ai challenge",
    ]],
    "formacion": [re.compile(p, re.IGNORECASE) for p in [
        r"scholarship", r"beca", r"fellowship", r"bootcamp", r"certification",
        r"research (program|symposium|seminar)", r"summer school", r"training program",
        r"course", r"curso", r"internship", r"mentorship",
    ]],
    "startups": [re.compile(p, re.IGNORECASE) for p in [
        r"accelerator", r"incubator", r"startup", r"founder", r"venture", r"pitch",
        r"entrepreneur", r"emprend",
    ]],
    "eventos": [re.compile(p, re.IGNORECASE) for p in [
        r"conference", r"summit", r"meetup", r"webinar", r"workshop", r"seminar",
        r"symposium", r"lecture", r"colloquium", r"panel", r"tech talk", r"demo day",
        r"hack day", r"meet-up", r"congress", r"congreso", r"conversation",
    ]],
}

TECH_HINTS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bai\b", r"artificial intelligence", r"machine learning", r"data", r"cloud",
    r"cyber", r"security", r"robot", r"software", r"developer", r"coding", r"program",
    r"technology", r"tech\b", r"digital", r"computer", r"engineering", r"startup",
    r"open source", r"blockchain", r"quantum", r"innovaci", r"inteligencia artificial",
    r"tecnolog", r"ciberseguridad", r"datos", r"videojuego", r"web\b", r"devops",
]]

_OPPORTUNITY_HINTS = [re.compile(p, re.IGNORECASE) for p in [
    r"hackathon", r"hackaton", r"datathon", r"challenge", r"reto", r"competition",
    r"concurso", r"scholarship", r"beca", r"fellowship", r"grant", r"accelerator",
    r"aceleradora", r"incubator", r"bootcamp", r"workshop", r"taller", r"conference",
    r"conferencia", r"summit", r"meetup", r"webinar", r"internship", r"practica",
    r"mentorship", r"course", r"curso", r"certification", r"open source", r"bounty",
    r"ctf", r"game jam", r"demo day", r"developer program", r"call for",
]]


def strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )


def looks_like_opportunity(*texts: str) -> bool:
    blob = " ".join(t for t in texts if t)
    if not blob.strip():
        return False
    return any(p.search(blob) for p in _OPPORTUNITY_HINTS)


def looks_tech(*texts: str) -> bool:
    blob = " ".join(t for t in texts if t)
    return any(p.search(blob) for p in TECH_HINTS)


def classify_category(*texts: str) -> str | None:
    """Best-effort category from title/description. None when evidence is weak."""
    blob = " ".join(t for t in texts if t)
    if not blob.strip():
        return None
    # Hackathons win when explicit: a "challenge" is usually a competition.
    for category in ("hackathons", "formacion", "startups", "eventos"):
        if any(p.search(blob) for p in CATEGORY_PATTERNS[category]):
            return category
    return None


def extract_tech_tags(*texts: str, limit: int = 6) -> list[str]:
    blob = " ".join(t for t in texts if t)
    tags = [tag for tag, patterns in TECH_PATTERNS.items() if any(p.search(blob) for p in patterns)]
    # De-duplicate near-synonyms: AI implies agents/ML only if explicit evidence exists.
    return tags[:limit]


def detect_modality(*texts: str) -> str:
    blob = " ".join(t for t in texts if t).lower()
    online = bool(re.search(r"\b(online|virtual|remote|remoto|en linea)\b", blob))
    onsite = bool(re.search(r"\b(in[- ]person|presencial|on[- ]site|onsite)\b", blob))
    if re.search(r"\bhybrid|hibrid", blob):
        return "hibrida"
    if online and onsite:
        return "hibrida"
    if online:
        return "online"
    if onsite:
        return "presencial"
    return "unknown"


def detect_cost(*texts: str) -> tuple[str, float | None]:
    blob = " ".join(t for t in texts if t).lower()
    if re.search(r"\b(free|gratis|gratuito|no cost|sin coste|free of charge)\b", blob):
        return "free", 0.0
    match = re.search(r"(?:USD|US\$|\$|EUR|€)\s?([0-9][0-9.,]{0,7})", blob)
    if match:
        raw = match.group(1).replace(",", "")
        try:
            return "paid", float(raw)
        except ValueError:
            return "paid", None
    return "unknown", None


def detect_language(text: str) -> str:
    """Cheap, explainable language hint; the UI shows it as a hint, never as fact."""
    lowered = text.lower()
    spanish = len(re.findall(r"\b(el|la|los|las|de|para|con|una|un|y|en|por|del|que)\b", lowered))
    english = len(re.findall(r"\b(the|and|for|with|from|this|that|you|are|will|of|to)\b", lowered))
    if spanish > english * 1.25 and spanish >= 3:
        return "es"
    if english > spanish * 1.25 and english >= 3:
        return "en"
    return "en"


def country_name(code: str | None) -> str | None:
    if not code:
        return None
    return COUNTRY_NAMES.get(code.upper(), code.upper())


def category_label(slug: str | None) -> str | None:
    if not slug:
        return None
    return CATEGORIES.get(slug, {}).get("label", slug)


def tech_label(slug: str) -> str:
    return TECH_TAGS.get(slug, {}).get("label", slug)

def looks_tech_strict(title: str, description: str = "") -> bool:
    """Stricter signal used for noisy calendars: title/description only, no location."""
    blob = f"{title} {description}".strip()
    if not blob:
        return False
    return any(p.search(blob) for p in STRICT_TECH_PATTERNS)


def classify_calendar_category(title: str, description: str = "") -> str | None:
    """Category classification for academic calendars, avoiding generic words like 'challenge'."""
    blob = f"{title} {description}".strip()
    for category in ("hackathons", "formacion", "startups", "eventos"):
        if any(p.search(blob) for p in CALENDAR_CATEGORY_PATTERNS[category]):
            return category
    return None
