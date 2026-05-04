import re
import hashlib
import settings
import storage
from notifier import Job

# job_level values from LinkedIn that indicate too much experience
SENIOR_LEVELS = {"director", "executive"}

# Minimum description length to not be considered spam
MIN_DESCRIPTION_LENGTH = 200

# words in title that indicate too much experience
SENIOR_TITLE_WORDS = [
    "senior", "lead", "expert", "confirmé", "expérimenté",
    "manager", "head", "directeur", "principal", "staff",
]


def is_relevant(title: str, company: str) -> bool:
    t = title.lower()
    c = company.lower()

    for blocked in settings.BLOCKED_COMPANIES:
        if blocked in c:
            return False

    for word in settings.BLOCKED_TITLE_WORDS:
        if re.search(rf"\b{re.escape(word.strip())}\b", t):
            return False

    # Pad with spaces so " bi " matches "bi analyst" at start of string too
    padded = f" {t} "
    has_role = any(w in padded for w in settings.REQUIRED_ROLE_WORDS)
    has_data = any(w in padded for w in settings.REQUIRED_DATA_WORDS)

    return has_role and has_data


def is_valid_location(job: Job) -> bool:
    """Only keep: remote jobs OR jobs physically in Montpellier/Lyon."""
    loc = (job.location or "").lower()

    # Always reject blocked cities/countries (even for "remote" jobs —
    # Luxembourg = different tax/legal jurisdiction; others are far/irrelevant)
    for blocked in settings.BLOCKED_LOCATION_KEYWORDS:
        if blocked in loc:
            return False

    if job.remote:
        return True
    if any(city.lower() in loc for city in settings.OFFICE_LOCATIONS):
        return True
    # Some sources return location="France" even for city-specific jobs.
    # Fall back to checking the title for the city name.
    if loc in ("france", ""):
        title = (job.title or "").lower()
        return any(city.lower() in title for city in settings.OFFICE_LOCATIONS)
    return False


def is_valid_experience(job: Job) -> bool:
    """Filter out jobs requiring 4+ years / senior level."""
    if job.experience_level:
        lvl = job.experience_level.lower()
        if lvl in SENIOR_LEVELS:
            return False
        # Catch numeric labels: "4 ans d'expérience", "5+ ans", "4-6 ans" etc.
        m = re.search(r"(\d+)\s*\+?\s*ans?", lvl)
        if m and int(m.group(1)) >= 4:
            return False

    title = (job.title or "").lower()
    for word in SENIOR_TITLE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", title):
            return False

    return True


def extract_exp_from_description(desc: str) -> tuple:
    """
    Parse years of experience required from description text.
    Returns (min_years: int|None, display_label: str|None).
    Handles French and English patterns.
    """
    if not desc:
        return None, None

    text = desc.lower()

    # "débutant accepté" / "profil junior" / "première expérience" → 0-1 an
    if re.search(r"d[ée]butant", text):
        return 0, "Junior (débutant accepté)"
    if re.search(r"premi[eè]re?\s+exp[eé]rience", text):
        return 0, "Première expérience acceptée"
    if re.search(r"profil\s+junior", text):
        return 0, "Profil junior"
    if re.search(r"junior\s+accept[eé]", text):
        return 0, "Junior accepté"
    if re.search(r"sans\s+exp[eé]rience", text):
        return 0, "Sans expérience requise"

    # Range: "1 à 3 ans", "2-3 ans", "0 to 2 years", "1–2 ans"
    m = re.search(r"(\d+)\s*(?:à|a|-|–|to)\s*(\d+)\s*an(?:s|née|nées)?", text)
    if not m:
        m = re.search(r"(\d+)\s*(?:à|a|-|–|to)\s*(\d+)\s*year", text)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if 0 <= lo <= 10 and lo <= hi:
            s = "ans" if hi > 1 else "an"
            return lo, f"{lo}-{hi} {s} d'expérience"

    # "X+ ans", "X ans minimum", "minimum X ans", "au moins X ans"
    m = re.search(r"(\d+)\s*\+\s*an(?:s|née)?", text)
    if not m:
        m = re.search(r"(\d+)\s*an(?:s|née)?\s*(?:minimum|min\b|requis|d'exp)", text)
    if not m:
        m = re.search(r"(?:minimum|min\b|au moins|at least)\s*(?:de\s*)?(\d+)\s*an", text)
    if not m:
        m = re.search(r"exp[eé]rience\s*(?:professionnelle\s*)?(?:de\s*)?[:\s]*(\d+)\s*an", text)
    if not m:
        m = re.search(r"justifi(?:ez|e)\s+d.{0,20}exp[eé]rience\s+(?:de\s*)?(\d+)", text)
    if not m:
        m = re.search(r"(\d+)\s*\+?\s*year", text)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 10:
            s = "ans" if n > 1 else "an"
            return n, f"{n} {s} d'expérience"

    # "expérience confirmée" / "expérience significative" → senior (filtre hors)
    if re.search(r"exp[eé]rience\s+(?:confirm[eé]e?|significative|solide|approfondie)", text):
        return 5, "Expérience confirmée (senior)"

    return None, None


def _years_from_label(label: str) -> int | None:
    """Extract the leading numeric year count from an experience label string."""
    if not label:
        return None
    low = label.lower()
    # Junior / débutant / no-exp signals → 0
    if any(w in low for w in ("débutant", "junior", "sans expérience", "première expérience")):
        return 0
    m = re.search(r"(\d+)", low)
    return int(m.group(1)) if m else None


def is_valid_domain(job: Job) -> bool:
    """Filter out jobs in irrelevant technical domains (checked in title + description)."""
    combined = f"{job.title} {job.description or ''}".lower()
    for kw in settings.BLOCKED_DOMAIN_KEYWORDS:
        if kw in combined:
            return False
    return True


def is_valid_description(job: Job, seen_hashes: set) -> bool:
    """
    Filter out ghost/spam jobs by description:
    - Skip if description is present but suspiciously short (< 200 chars)
    - Skip if contains known ghost-job phrase (e.g. "after 27 applicants")
    - Skip if same description template was seen this run OR in a previous run
    If description is None (source doesn't provide it), let the job through.
    """
    desc = job.description
    if desc is None:
        return True  # source doesn't return description — can't judge

    desc_clean = desc.strip()
    if not desc_clean:
        return True  # empty string = no data from source, let through

    if len(desc_clean) < MIN_DESCRIPTION_LENGTH:
        return False  # too short → likely spam / placeholder

    # Check for known ghost-job / spam template phrases
    desc_lower = desc_clean.lower()
    for phrase in settings.BLOCKED_DESCRIPTION_PHRASES:
        if phrase in desc_lower:
            return False

    # Hash first 500 chars (normalised) to detect identical templates
    snippet = " ".join(desc_clean[:500].lower().split())
    h = hashlib.md5(snippet.encode()).hexdigest()

    # In-run dedup
    if h in seen_hashes:
        return False
    seen_hashes.add(h)

    # Cross-run dedup: reject if this exact template was seen before
    if storage.is_desc_hash_seen(h):
        return False
    storage.add_desc_hash(h)

    return True


def score(title: str) -> int:
    """Higher score = more relevant. Used to sort alerts before sending."""
    t = title.lower()
    return sum(1 for term in settings.SCORE_BOOST_TERMS if term in t)
