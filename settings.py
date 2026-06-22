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
    # operations
    "operations analyst",
    # HR / people
    "hr analyst",
    "people analyst",
    "analyste rh",
    # market research
    "market research analyst",
]

OFFICE_LOCATIONS = ["Montpellier", "Lyon"]

# bot runs every 2h, 6h = 3 runs of buffer — reduces missed jobs without flooding
MAX_JOB_AGE_HOURS = 6

# companies that spam job boards with gig/survey/non-relevant postings
BLOCKED_COMPANIES = [
    "prolific", "alignerr", "mercor", "remotasks", "appen", "jobgether",
    "telus international", "outlier", "scale ai", "clickworker", "peaktew",
    # ESN / IT consulting firms (post IT-BA / AMOA jobs, not data analyst)
    "sopra steria", "sopra ", "amiltone", "it link", "alteca", "amaris", "celad",
    "argain", "nexton", "consultys", "alcyor", "shape it",
    "collective.work", "collectivework",
    "akkodis", "capgemini", "extia", "caveo", "coexya", "alten", "atos ",
    "cgi ", "devoteam", "talan",
    # Gaming / gambling operators
    "b2spin", "patrianna",
    # Job aggregators that repost others' jobs under their own name
    "jobgether",
]

# phrases in job description that indicate a ghost/spam template job
# matched against lowercased description text
BLOCKED_DESCRIPTION_PHRASES = [
    # Fake LinkedIn "auto-close after N applicants" ghost jobs
    "after 27 applicants",
    "after 27 candidatures",
    "automatically closing after 27",
    "closes after 27",
    "closing after 27",
    # Other known ghost job signals
    "submit your cv for consideration",
]

# job titles containing these words are always skipped
BLOCKED_TITLE_WORDS = [
    "stage", "stagiaire", "alternance", "alternant", "alternante",
    "apprenticeship", "apprentice", "apprenti", "apprentie",
    "internship", "intern", "intérim", "interim", "pfm", "pfe",
    "senior", "lead ", "expert ", "manager ", "head of",
    "directeur", "director", "chef de", "responsable de",
    "confirmé", "confirme", "expérimenté", "experimente",
    "study participants", "data annotator", "ai trainer",
    "auditeur", "payroll", "restauration",
    "transformation digitale",
    # IT/AMOA functional analyst (not data/BI)
    "amoa", " moa ", "maîtrise d'ouvrage", "fonctionnel",
    # ERP/ITSM/developer specialist roles
    "servicenow", "workday", "dynamics 365",
    # Pricing (too niche / irrelevant)
    "pricing",
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
    "operations analyst",
    "hr analyst", "people analyst", "market research",
    "sql", "python", "tableau", "looker",
    # Tool combinations (strong BI signal)
    "sql et python", "python et sql", "power bi et sql", "sql + python",
    # Top-fit industries & analytics disciplines
    "product analytics", "marketing analytics", "growth analytics",
    "média", "media", "streaming", "contenu", "content",
    "saas", "startup", "scale-up",
    "marketplace", "e-commerce", "ecommerce",
    "performance commerciale", "kpi", "dashboard", "tableau de bord",
]

# Companies that are a strong profile match — get +2 score bonus.
# Checked against company name (lowercased, partial match).
PREFERRED_COMPANIES = [
    # Media / Creator Economy
    "jellysmack", "brut", "dailymotion", "canal", "webedia", "prisma",
    # SaaS / Tech startups
    "agicap", "pennylane", "partoo", "swile", "contentsquare",
    # E-commerce / Marketplace
    "cdiscount", "veepee", "manomano", "vinted",
    # Digital agencies / Analytics consulting
    "artefact", "fifty-five", "jellyfish", "converteo",
    # Lyon-based companies that hire regularly
    "biomerieux", "bioxmerieux", "sanofi", "gl events", "infopro", "cegid",
]

# keywords in description/title that indicate irrelevant technical domain
# checked against combined title + description text (lowercased)
BLOCKED_DOMAIN_KEYWORDS = [
    # Payment / card processing
    "monétique", "monetique", "acquiring", "billettique",
    # Finance protocols
    "t2s ", "target2",
    # Insurance sub-domain
    " iard ",
    # Aerospace / defense
    "aéronautique", "aeronautique", "défense nationale",
    # Pharma / life sciences (highly specialized, not BI-generalist)
    " pharma", "biotech", "life sciences", "sciences de la vie", " lims ",
    # Supply chain / logistics specialist
    "supply chain",
    # Gaming / gambling
    "casino", "gambling", "social gaming",
    # IT tools indicating specialist (not analyst) role
    "dynamics 365", "dynamics365", "gainsight", " cpq ",
    # IT BA / AMOA signals in description (writing specs/testing, not analyzing data)
    "spécifications fonctionnelles", "user stories", " uml ",
    "architecture si", "architecture du si",
    " bpmn ", "recette fonctionnelle", "tests de recette", " tnr ",
    # Salesforce developer tools (not BI)
    "salesforce field service", " apex ", "salesforce apex",
    # Insurance / banking / mutual fund sector (generates AMOA BA jobs)
    "secteur bancaire", "secteur de l'assurance", " mutuelle ", " prévoyance ",
    " prevoyance ", "bancaire",
]

# location substrings always rejected (hard override — wins over the EU allowlist)
# Luxembourg → EU but different tax/legal jurisdiction, kept out on purpose.
# Small irrelevant French cities → not worth relocating.
BLOCKED_LOCATION_KEYWORDS = [
    # Non-France countries (redundant with the allowlist, kept as explicit guard)
    "canada", "états-unis", "etats-unis", "united states", " usa", "gibraltar",
    # EU but excluded on purpose (tax jurisdiction)
    "luxembourg",
    # Small/irrelevant French cities (these rarely post true remote)
    "niort", "bartenheim", "chaumont", "limoges",
]

# Allowlist of accepted countries for REMOTE jobs: France + EU/EEA.
# A remote job passes the location filter only if its location names one of
# these (or a target office city). UK and Switzerland are intentionally absent.
# Matched as lowercase substrings against the job's location string.
EUROPEAN_COUNTRIES = [
    "france",
    "allemagne", "germany", "deutschland",
    "espagne", "spain", "españa",
    "italie", "italy", "italia",
    "portugal",
    "belgique", "belgium", "belgië",
    "pays-bas", "netherlands", "nederland",
    "irlande", "ireland",
    "autriche", "austria", "österreich",
    "pologne", "poland", "polska",
    "suède", "suede", "sweden",
    "danemark", "denmark",
    "finlande", "finland",
    "grèce", "grece", "greece",
    "tchèque", "tcheque", "tchéquie", "czech", "czechia",
    "roumanie", "romania",
    "hongrie", "hungary",
    "bulgarie", "bulgaria",
    "croatie", "croatia",
    "slovaquie", "slovakia",
    "slovénie", "slovenie", "slovenia",
    "lituanie", "lithuania",
    "lettonie", "latvia",
    "estonie", "estonia",
    "chypre", "cyprus",
    "malte", "malta",
    # EEA (non-EU)
    "norvège", "norvege", "norway", "norge",
    "islande", "iceland",
    "liechtenstein",
]

# Minimum annual salary in EUR — jobs with salary explicitly below this are skipped.
# Only applied when salary is clearly stated; unknown salary = not filtered.
MIN_ANNUAL_SALARY_EUR = 35000
