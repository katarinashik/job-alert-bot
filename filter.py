import re
import settings


def is_relevant(title: str, company: str) -> bool:
    t = title.lower()
    c = company.lower()

    # blocked companies
    for blocked in settings.BLOCKED_COMPANIES:
        if blocked in c:
            return False

    # blocked title words
    for word in settings.BLOCKED_TITLE_WORDS:
        if re.search(rf"\b{re.escape(word.strip())}\b", t):
            return False

    # must have analyst/analyste + a data-related word
    has_role = any(w in t for w in settings.REQUIRED_ROLE_WORDS)
    has_data = any(w in t for w in settings.REQUIRED_DATA_WORDS)

    return has_role and has_data


def score(title: str) -> int:
    """Higher score = more relevant. Used to sort alerts before sending."""
    t = title.lower()
    return sum(1 for term in settings.SCORE_BOOST_TERMS if term in t)
