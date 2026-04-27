SEARCH_KEYWORDS = [
    # core data / BI
    "data analyst",
    "analyste données",
    "analyste de données",
    "bi analyst",
    "analyste bi",
    "business intelligence analyst",
    "reporting analyst",
    "analyste reporting",
    "growth analyst",
    "marketing analyst",
    "analyste marketing",
    # business
    "business analyst",
    "analyste métier",
    # web / digital / e-commerce
    "web analyst",
    "digital analyst",
    "analyste web",
    "analyste digital",
    "e-commerce analyst",
    "analyste e-commerce",
    # CRM / product
    "crm analyst",
    "analyste crm",
    "product analyst",
    "analyste produit",
    # operations / pricing
    "operations analyst",
    "pricing analyst",
    "analyste pricing",
    # HR / people
    "hr analyst",
    "people analyst",
    "analyste rh",
    # market research
    "market research analyst",
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
    "transformation digitale",
]

# title must contain at least one of these groups to be considered relevant
# group A: role contains "analyst/analyste"
# group B: topic contains data/bi/reporting/etc.
REQUIRED_ROLE_WORDS = ["analyst", "analyste"]
REQUIRED_DATA_WORDS = [
    "data", " bi ", "power bi", "reporting", "insight", "growth", "analytics",
    "marketing", "business",
    "web", "digital", "e-commerce", "ecommerce",
    "crm", "product", "produit",
    "operations", "opérations",
    "pricing", "prix",
    "people", "market",
]

# high-value terms that boost score (the more the better)
SCORE_BOOST_TERMS = [
    "junior", "data analyst", "analyste données", "analyste de données",
    "power bi", "bi analyst", "analyste bi",
    "insight", "growth", "reporting",
    "marketing analyst", "business analyst", "analyste métier",
    "web analyst", "digital analyst", "e-commerce analyst",
    "crm analyst", "product analyst", "analyste produit",
    "pricing analyst", "operations analyst",
    "hr analyst", "people analyst", "market research",
    "sql", "python", "tableau", "looker",
]
