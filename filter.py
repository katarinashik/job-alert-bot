import re
import settings
from notifier import Job

# job_level values from LinkedIn that indicate too much experience
SENIOR_LEVELS = {"director", "executive"}

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

    has_role = any(w in t for w in settings.REQUIRED_ROLE_WORDS)
    has_data = any(w in t for w in settings.REQUIRED_DATA_WORDS)

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
        if job.experience_level.lower() in SENIOR_LEVELS:
            return False

    title = (job.title or "").lower()
    for word in SENIOR_TITLE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", title):
            return False

    return True


def score(title: str) -> int:
    """Higher score = more relevant. Used to sort alerts before sending."""
    t = title.lower()
    return sum(1 for term in settings.SCORE_BOOST_TERMS if term in t)
