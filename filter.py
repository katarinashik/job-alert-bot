import re
import hashlib
import settings
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
    if job.remote:
        return True
    loc = (job.location or "").lower()
    return any(city.lower() in loc for city in settings.OFFICE_LOCATIONS)


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


def is_valid_description(job: Job, seen_hashes: set) -> bool:
    """
    Filter out ghost/spam jobs by description:
    - Skip if description is present but suspiciously short (< 200 chars)
    - Skip if another job this run had the exact same description text
      (same template copy-pasted across companies)
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

    # Hash first 500 chars (normalised) to detect identical templates
    snippet = " ".join(desc_clean[:500].lower().split())
    h = hashlib.md5(snippet.encode()).hexdigest()
    if h in seen_hashes:
        return False  # duplicate description already seen this run
    seen_hashes.add(h)
    return True


def score(title: str) -> int:
    """Higher score = more relevant. Used to sort alerts before sending."""
    t = title.lower()
    return sum(1 for term in settings.SCORE_BOOST_TERMS if term in t)
