from __future__ import annotations

import hashlib
import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = _TAG_RE.sub(" ", value)
    value = _WS_RE.sub(" ", value).strip()
    return value


def description_hash(text: str) -> str:
    normalized = clean_text(text).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _slug(text: str | None) -> str:
    if not text:
        return ""
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9а-яёäöüß]+", "-", text, flags=re.IGNORECASE)
    return text.strip("-")


_DE_MARKERS = {
    "aufgaben", "anforderungen", "wir suchen", "wir bieten", "stellenbeschreibung",
    "ihr profil", "ihre aufgaben", "kenntnisse", "bewerbung", "vollzeit", "teilzeit",
    "berufserfahrung", "deutsch", "unbefristet", "standort",
}


def detect_language(text: str) -> str:
    """Heuristic: returns 'de' if text looks German, else 'en'."""
    sample = clean_text(text)[:1000].lower()
    hits = sum(1 for marker in _DE_MARKERS if marker in sample)
    return "de" if hits >= 2 else "en"


def build_dedup_key(
    title: str | None,
    company: str | None,
    place: str | None,
    desc: str | None,
) -> str:
    head = f"{_slug(title)}|{_slug(company)}|{_slug(place)}"
    tail = hashlib.sha1(
        clean_text(desc)[:500].lower().encode("utf-8")
    ).hexdigest()
    return f"{head}|{tail}"
