import re
import hashlib
import settings
import storage
from notifier import Job

# job_level values from LinkedIn that indicate too much experience
SENIOR_LEVELS = {"director", "executive"}

_PARIS_SIGNALS = [
    " paris ", "paris,", "paris\n", "(paris)", "paris 1", "paris 2",
    "paris 3", "paris 4", "paris 5", "paris 6", "paris 7", "paris 8",
    "paris 9", "paris 10", "paris 11", "paris 12", "paris 13",
    "paris 14", "paris 15", "paris 16", "paris 17", "paris 18",
    "paris 19", "paris 20",
    "75001", "75002", "75003", "75004", "75005", "75006", "75007",
    "75008", "75009", "75010", "75011", "75012", "75013", "75014",
    "75015", "75016", "75017", "75018", "75019", "75020",
    "île-de-france", "ile-de-france",
    "levallois", "boulogne-billancourt", "neuilly-sur-seine",
    "la défense", "la defense",
]

_FULL_REMOTE_SIGNALS = [
    "100% remote", "100% télétravail", "full remote", "fully remote",
    "télétravail complet", "full télétravail", "remote first",
    "remote-first", "remote only", "entièrement en télétravail",
    "100 % télétravail",
]


def _is_paris_only(job: Job) -> bool:
    loc = (job.location or "").lower()
    if "paris" in loc and not any(c.lower() in loc for c in settings.OFFICE_LOCATIONS):
        return True
    desc = (job.description or "").lower()
    if not desc:
        return False
    if any(sig in desc for sig in _FULL_REMOTE_SIGNALS):
        return False
    header = desc[:400]
    return any(sig in header for sig in _PARIS_SIGNALS)

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
        if _is_paris_only(job):
            return False
        return True
    if any(city.lower() in loc for city in settings.OFFICE_LOCATIONS):
        return True
    # Some sources return location="France" even for city-specific jobs.
    # Search city in title AND description — more reliable than title alone.
    if loc in ("france", ""):
        text = f"{job.title or ''} {job.description or ''}".lower()
        return any(city.lower() in text for city in settings.OFFICE_LOCATIONS)
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


def _parse_annual_salary(salary_str: str) -> float | None:
    """Extract minimum annual salary in EUR from various format strings."""
    if not salary_str:
        return None
    s = salary_str.lower()
    # France Travail: "annuel de 28000.0 euros à 32000.0 euros"
    m = re.search(r"annuel\s+de\s+([\d.]+)", s)
    if m:
        return float(m.group(1))
    # jobspy: "28,000–32,000 €/yearly" or "from 28,000 €/yearly"
    if "year" in s or "/an" in s or "annuel" in s:
        nums = re.findall(r"\d[\d\s,]*\d|\d+", s.replace(",", "").replace(" ", ""))
        nums = [int(n) for n in nums if len(n) >= 4]
        if nums:
            return float(min(nums))
    # "32k€" or "32 k€"
    m = re.search(r"(\d+)\s*k", s)
    if m:
        return float(m.group(1)) * 1000
    return None


def is_valid_salary(job: "Job") -> bool:
    """Return False only if salary is explicitly stated and below the minimum."""
    annual = _parse_annual_salary(job.salary or "")
    if annual is None:
        return True  # unknown salary → don't filter
    return annual >= settings.MIN_ANNUAL_SALARY_EUR


def score(title: str, company: str = "") -> int:
    """Higher score = more relevant. Used to sort alerts before sending."""
    t = title.lower()
    c = company.lower()
    s = sum(1 for term in settings.SCORE_BOOST_TERMS if term in t)
    # +2 bonus for top-fit companies (profile match)
    if any(pref in c for pref in settings.PREFERRED_COMPANIES):
        s += 2
    return s


# ── Fit score ────────────────────────────────────────────────────────────────
# Weighted keyword groups — scored against title + full description text.
# Each group has a cap so one signal can't dominate the score.

_FIT_TOOLS = {          # max 35 pts — BI/analytics tools
    "power bi": 10, "powerbi": 10,
    "looker studio": 8, "looker": 7,
    "google data studio": 7, "google analytics": 5,
    "tableau": 7, "metabase": 5, "amplitude": 5, "mixpanel": 5,
    "sql": 9, "python": 8,
    "excel": 3, "google sheets": 2,
    "dbt": 4, "airflow": 3, "bigquery": 4, "snowflake": 3,
}

_FIT_ROLE = {           # max 30 pts — BI/analytics work signals
    "dashboard": 6, "tableau de bord": 6,
    "kpi": 5, "indicateurs": 4,
    "reporting": 5, "rapport": 3,
    "product analytics": 7, "marketing analytics": 7, "growth analytics": 6,
    "a/b test": 5, "ab test": 5, "test a/b": 5,
    "visualisation": 4, "data viz": 4,
    "performance commerciale": 5, "analyse commerciale": 5,
    "entrepôt de données": 4, "datawarehouse": 4, "data warehouse": 4,
}

_FIT_INDUSTRY = {       # max 25 pts — industries matching candidate background
    "saas": 12, "startup": 9, "scale-up": 9,
    "e-commerce": 10, "ecommerce": 10, "marketplace": 10,
    "média": 9, "media": 9, "streaming": 9, "contenu": 6, "content": 6,
    "retail": 6, "fmcg": 6, "digital": 5, "tech": 5,
}

_FIT_LEVEL = {          # max 10 pts — junior-friendly signals
    "junior": 10, "débutant": 10, "sans expérience": 10,
    "première expérience": 9, "0-2 ans": 9, "1-2 ans": 8, "1-3 ans": 7,
}


def fit_score(job: Job) -> int:
    """
    Calculate candidate fit percentage (0–100) from job description content.
    Based on BI tools, analytics work signals, industry match, and level fit.
    """
    combined = f"{job.title} {job.description or ''}".lower()

    tools_pts    = min(35, sum(v for k, v in _FIT_TOOLS.items()    if k in combined))
    role_pts     = min(30, sum(v for k, v in _FIT_ROLE.items()     if k in combined))
    industry_pts = min(25, sum(v for k, v in _FIT_INDUSTRY.items() if k in combined))
    level_pts    = min(10, sum(v for k, v in _FIT_LEVEL.items()    if k in combined))

    # Neutral industry baseline so "unknown industry" doesn't score 0
    if industry_pts == 0:
        industry_pts = 6

    # Preferred company bonus (replaces company-type penalty for ESNs already filtered)
    company_bonus = 5 if any(p in job.company.lower() for p in settings.PREFERRED_COMPANIES) else 0

    return min(100, tools_pts + role_pts + industry_pts + level_pts + company_bonus)
