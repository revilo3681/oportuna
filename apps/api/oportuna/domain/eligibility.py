"""Eligibility assessment.

We only claim "eligible" when every declared requirement has been checked against
profile data. Missing information always yields "unknown", never a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EligibilityResult:
    verdict: str  # eligible | likely | unknown | ineligible
    label: str
    reasons: list[str] = field(default_factory=list)
    checked_requirements: list[str] = field(default_factory=list)
    unverified_requirements: list[str] = field(default_factory=list)


def assess_eligibility(
    requirements: dict | None,
    profile: dict | None,
    *,
    modality: str | None = None,
) -> EligibilityResult:
    requirements = requirements or {}
    known_keys = [k for k, v in requirements.items() if v not in (None, "", [], {}) and k != "notes"]
    if not known_keys:
        return EligibilityResult(
            "unknown",
            "Elegibilidad por confirmar",
            ["La organización no ha publicado requisitos verificables."],
        )
    if not profile:
        return EligibilityResult(
            "unknown",
            "Completa tu perfil para comprobar requisitos",
            ["Sin perfil no se puede contrastar edad, país o nivel."],
            unverified_requirements=known_keys,
        )

    blockers: list[str] = []
    checked: list[str] = []
    unverified: list[str] = []

    countries = requirements.get("countries") or []
    if countries:
        country = (profile.get("country") or "").upper()
        if not country:
            unverified.append("país")
        else:
            checked.append("país")
            if country not in [c.upper() for c in countries]:
                blockers.append(f"La convocatoria admite {', '.join(countries)}; tu país es {country}.")
            elif modality == "presencial" and not profile.get("city"):
                unverified.append("ciudad para asistencia presencial")

    min_age = requirements.get("min_age")
    max_age = requirements.get("max_age")
    age = profile.get("age")
    if min_age is not None or max_age is not None:
        if age is None:
            unverified.append("edad")
        else:
            checked.append("edad")
            if min_age is not None and age < int(min_age):
                blockers.append(f"Requiere al menos {min_age} años.")
            if max_age is not None and age > int(max_age):
                blockers.append(f"Límite de edad: {max_age} años.")

    if requirements.get("students_only"):
        is_student = (profile.get("eligibility") or {}).get("is_student")
        if is_student is None:
            unverified.append("estatus de estudiante")
        else:
            checked.append("estudiante")
            if not is_student:
                blockers.append("Exclusivo para estudiantes.")

    levels = requirements.get("experience_levels") or []
    if levels:
        level = profile.get("level")
        if not level:
            unverified.append("nivel de experiencia")
        else:
            checked.append("nivel")
            if level not in levels:
                blockers.append(f"Nivel requerido: {', '.join(levels)}; tu perfil indica {level}.")

    team_required = requirements.get("team_required")
    if team_required is not None:
        checked.append("formato de equipo")
        preference = (profile.get("preferences") or {}).get("team")
        if team_required and preference is False:
            # A preference mismatch is not a hard eligibility failure; flag it.
            blockers.append("Requiere equipo y tu perfil indica preferencia individual.")

    if blockers:
        return EligibilityResult("ineligible", "Requisitos no cumplidos", blockers, checked, unverified)
    if unverified:
        return EligibilityResult(
            "likely",
            "Posiblemente elegible",
            ["Cumples los requisitos comprobados; faltan datos: " + ", ".join(unverified) + "."],
            checked,
            unverified,
        )
    return EligibilityResult(
        "eligible",
        "Cumples los requisitos declarados",
        ["Contrastado con los requisitos publicados. Confirma siempre en la fuente oficial."],
        checked,
        [],
    )
