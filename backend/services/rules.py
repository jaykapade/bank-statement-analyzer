"""
Rules-based pre-categorization engine.

Runs BEFORE LLM categorization to handle well-known merchants deterministically.
Only transactions that don't match any rule are forwarded to the LLM.

Rule matching:
- Case-insensitive substring match on the transaction description
- First matching rule wins (rules ordered from most specific → most general)
- Returns (matched, unmatched) — matched items have a "category" key added
"""

import re
from logger import logger

# ---------------------------------------------------------------------------
# Category Rules
# Each rule: {"keywords": [...], "patterns": [...], "category": str}
# At least one of keywords/patterns is required.
# keywords: case-insensitive substring match
# patterns: case-insensitive regex match
# ---------------------------------------------------------------------------
RULES: list[dict] = [
    # -----------------------------------------------------------------------
    # FOOD
    # -----------------------------------------------------------------------
    {
        "category": "Food",
        "keywords": [
            "swiggy",
            "zomato",
            "blinkit",
            "zepto",
            "dunzo",
            "domino",
            "pizza hut",
            "kfc",
            "mcdonald",
            "burger king",
            "subway",
            "starbucks",
            "cafe coffee day",
            "ccd",
            "haldiram",
            "amul",
            "instacart",
            "bigbasket",
            "grofers",
            "bbnow",
            "fresh to home",
            "licious",
            "country delight",
            "milkbasket",
            "eatfit",
            "box8",
            "freshmenu",
            "faasos",
            "behrouz",
            "ovenstory",
            "wendy",
            # common generic food tokens
            "restaurant",
            "bakery",
            "dhaba",
            "canteen",
            "juice bar",
        ],
    },
    # -----------------------------------------------------------------------
    # HEALTH
    # -----------------------------------------------------------------------
    {
        "category": "Health",
        "keywords": [
            "apollo",
            "medplus",
            "netmeds",
            "1mg",
            "tata 1mg",
            "practo",
            "pharmeasy",
            "lenskart",
            "max hospital",
            "fortis",
            "manipal hospital",
            "narayana health",
            "thyrocare",
            "dr lal",
            "lalpath",
            "metropolis",
            "aiims",
            "cipla",
            "sun pharma",
            "healthkart",
            "cult.fit",
            "cure.fit",
            "fitpass",
            # generic
            "pharmacy",
            "chemist",
            "medical store",
            "diagnostic",
            "hospital",
            "clinic",
            "nursing home",
        ],
    },
    # -----------------------------------------------------------------------
    # TRAVEL
    # -----------------------------------------------------------------------
    {
        "category": "Travel",
        "keywords": [
            "irctc",
            "redbus",
            "makemytrip",
            "make my trip",
            "goibibo",
            "yatra",
            "cleartrip",
            "ixigo",
            "booking.com",
            "airbnb",
            "oyo",
            "fabhotels",
            "treebo",
            "air india",
            "indigo",
            "spicejet",
            "vistara",
            "go first",
            "akasa",
            "air asia",
            "jetblue",
            "emirates",
            "singapore airlines",
            "ola",
            "uber",
            "rapido",
            "meru",
            "bluebird",
            "fastag",
            "nhai",
            "toll",
            "petrol",
            "fuel",
            "hp petrol",
            "indian oil",
            "iocl",
            "bharat petroleum",
            "bpcl",
            "shell",
        ],
        "patterns": [
            r"\birctc\b",
            r"train\s*ticket",
            r"flight\s*ticket",
            r"bus\s*ticket",
        ],
    },
    # -----------------------------------------------------------------------
    # SHOPPING
    # -----------------------------------------------------------------------
    {
        "category": "Shopping",
        "keywords": [
            "amazon",
            "flipkart",
            "myntra",
            "meesho",
            "ajio",
            "nykaa",
            "purplle",
            "tata cliq",
            "snapdeal",
            "shopclues",
            "reliance digital",
            "croma",
            "vijay sales",
            "apple store",
            "samsung",
            "oneplus",
            "d-mart",
            "dmart",
            "spencer",
            "big bazaar",
            "more supermarket",
            "star bazaar",
            "spar",
            "ikea",
            "pepperfry",
            "urban ladder",
            "firstcry",
            "babyoye",
            "decathlon",
            "lifestyle",
            "shoppers stop",
            "westside",
            "pantaloons",
            "max fashion",
            "zara",
            "h&m",
        ],
    },
    # -----------------------------------------------------------------------
    # BILLS (subscriptions, utilities, insurance, telecom, loan payments)
    # -----------------------------------------------------------------------
    {
        "category": "Bills",
        "keywords": [
            # Streaming / subscriptions
            "netflix",
            "spotify",
            "prime video",
            "amazon prime",
            "hotstar",
            "disney+",
            "zee5",
            "sonyliv",
            "voot",
            "youtube premium",
            "apple tv",
            "tinder",
            "bumble",
            "linkedin premium",
            # Telecom
            "airtel",
            "jio",
            "vi ",
            "vodafone",
            "bsnl",
            "mtnl",
            "act fibernet",
            "hathway",
            "tikona",
            # Utilities
            "electricity",
            "bescom",
            "mseb",
            "tata power",
            "adani electricity",
            "bses",
            "tneb",
            "kseb",
            "water bill",
            "gas bill",
            "piped gas",
            "mahanagargas",
            "igl",
            "atgl",
            # Insurance
            "insurance",
            "lic",
            "hdfc life",
            "sbi life",
            "icici prudential",
            "bajaj allianz",
            "star health",
            "niva bupa",
            "max bupa",
            "new india assurance",
            # Loan / EMI
            "emi",
            "loan repayment",
            "ecs debit",
            "nach debit",
            # Generic
            "bill payment",
            "recharge",
            "broadband",
        ],
        "patterns": [
            r"\bemi\b",
            r"\bnach\b",
            r"\becs\b",
            r"credit\s*card\s*(payment|bill|due)",
        ],
    },
    # -----------------------------------------------------------------------
    # OTHER  (wallets, bank fees, transfers — catch-all, keep last)
    # -----------------------------------------------------------------------
    {
        "category": "Other",
        "keywords": [
            "paytm",
            "phonepe",
            "phone pe",
            "gpay",
            "google pay",
            "amazon pay",
            "mobikwik",
            "freecharge",
            "bank charge",
            "service charge",
            "annual fee",
            "processing fee",
            "late payment fee",
            "interest charged",
            "finance charge",
            "neft",
            "rtgs",
            "imps",
            "upi",
        ],
    },
]


# ---------------------------------------------------------------------------
# Compiled rule cache (built once on first call)
# ---------------------------------------------------------------------------
_compiled: list[dict] | None = None


def _compile_rules() -> list[dict]:
    compiled = []
    for rule in RULES:
        entry: dict = {"category": rule["category"], "keywords": [], "patterns": []}
        for kw in rule.get("keywords", []):
            entry["keywords"].append(kw.lower())
        for pat in rule.get("patterns", []):
            entry["patterns"].append(re.compile(pat, re.IGNORECASE))
        compiled.append(entry)
    return compiled


def _get_compiled() -> list[dict]:
    global _compiled
    if _compiled is None:
        _compiled = _compile_rules()
    return _compiled


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def match_category(description: str) -> str | None:
    """
    Return the first matching category for a transaction description,
    or None if no rule matches.
    """
    desc_lower = description.lower()
    for rule in _get_compiled():
        for kw in rule["keywords"]:
            if kw in desc_lower:
                return rule["category"]
        for pat in rule["patterns"]:
            if pat.search(description):
                return rule["category"]
    return None


def rules_categorize(transactions: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Split transactions into rule-matched and LLM-needed lists.

    Each transaction dict must have at least: id, description, date, amount.
    Matched transactions gain a "category" key.

    Returns:
        matched   — transactions with category assigned by rules
        unmatched — transactions that need LLM categorization
    """
    matched: list[dict] = []
    unmatched: list[dict] = []

    for txn in transactions:
        desc = txn.get("description", "")
        category = match_category(desc)
        if category:
            matched.append({**txn, "category": category})
        else:
            unmatched.append(txn)

    logger.info(
        f"[Rules] {len(matched)} pre-categorized by rules, "
        f"{len(unmatched)} forwarded to LLM"
    )
    return matched, unmatched
