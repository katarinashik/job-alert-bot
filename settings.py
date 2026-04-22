SEARCH_KEYWORDS = [
    "junior data analyst",
    "junior analyste données",
    "junior bi analyst",
    "junior power bi analyst",
    "junior insight analyst",
    "junior growth analyst",
    "junior marketing data analyst",
    "junior reporting analyst",
    "analyste données junior",
    "analyste bi junior",
    "analyste reporting junior",
]

OFFICE_LOCATIONS = ["Montpellier", "Lyon"]

# keep small — bot runs every 2h, 4h gives a safe buffer without flooding on restart
MAX_JOB_AGE_HOURS = 4

# companies that spam job boards with gig/survey/non-relevant postings
BLOCKED_COMPANIES = [
    "prolific",
    "alignerr",
    "mercor",
    "remotasks",
    "appen",
    "telus international",
    "outlier",
    "scale ai",
    "clickworker",
]

# job titles containing these words are always skipped
BLOCKED_TITLE_WORDS = [
    "stage", "stagiaire", "alternance", "alternant", "alternante",
    "apprenticeship", "apprentice", "apprenti", "apprentie",
    "internship", "intern", "pfm", "pfe",
    "senior", "lead ", "expert ", "manager ", "head of",
    "directeur", "director", "chef de", "responsable de",
    "confirmé", "confirme", "expérimenté", "experimente",
    "study participants", "data annotator", "ai trainer",
    "auditeur", "payroll", "restauration",
]

# title must contain at least one of these groups to be considered relevant
# group A: role contains "analyst/analyste"
# group B: topic contains data/bi/reporting/etc.
REQUIRED_ROLE_WORDS = ["analyst", "analyste"]
REQUIRED_DATA_WORDS = ["data", " bi ", "power bi", "reporting", "insight", "growth", "analytics", "marketing data"]

# high-value terms that boost score (the more the better)
SCORE_BOOST_TERMS = [
    "junior", "data analyst", "analyste données", "analyste de données",
    "power bi", "bi analyst", "analyste bi",
    "insight", "growth", "reporting", "marketing analyst",
    "sql", "python", "tableau", "looker",
]
