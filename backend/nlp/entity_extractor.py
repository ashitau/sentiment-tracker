"""
Named Entity Recognition tuned for Indian financial text.
Handles Hinglish, ticker aliases, and sector taxonomy resolution.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
import spacy
from loguru import logger

# NSE 500 ticker → canonical name (abbreviated — extend with full list)
TICKER_ALIASES: dict[str, str] = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "ICICIBANK": "ICICI Bank",
    "HINDUNILVR": "Hindustan Unilever",
    "SBIN": "State Bank of India",
    "WIPRO": "Wipro",
    "TATAMOTORS": "Tata Motors",
    "ONGC": "Oil and Natural Gas Corporation",
    "SUNPHARMA": "Sun Pharmaceutical",
    "DRREDDY": "Dr Reddy's Laboratories",
    "MARUTI": "Maruti Suzuki",
    "BAJFINANCE": "Bajaj Finance",
    "AXISBANK": "Axis Bank",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro",
    "ITC": "ITC Limited",
    "TITAN": "Titan Company",
    "ASIANPAINT": "Asian Paints",
}

# Common colloquial aliases
COLLOQUIAL_MAP: dict[str, str] = {
    "Tata Sons": "Tata Group",
    "TML": "Tata Motors",
    "HDFC Life": "HDFC Life Insurance",
    "Bajaj Fin": "Bajaj Finance",
    "Kotak": "Kotak Mahindra Bank",
    "RIL": "Reliance Industries",
    "SBI": "State Bank of India",
}

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Banking & Finance": ["bank", "nbfc", "loan", "credit", "rbi", "interest rate", "repo", "npa", "fintech"],
    "Information Technology": ["it sector", "software", "tech", "saas", "digital", "cloud", "ai", "infosys", "tcs", "wipro"],
    "Energy": ["oil", "gas", "petroleum", "ongc", "reliance", "renewable", "solar", "wind energy"],
    "Automobile": ["auto", "ev", "electric vehicle", "car sales", "maruti", "tata motors", "mahindra"],
    "Pharmaceuticals": ["pharma", "drug", "fda", "usfda", "medicine", "biotech", "sun pharma"],
    "FMCG": ["fmcg", "consumer goods", "hul", "itc", "dabur", "nestle", "marico"],
    "Real Estate": ["real estate", "realty", "housing", "dlf", "godrej properties", "oberoi"],
    "Metals & Mining": ["steel", "metal", "aluminium", "copper", "coal", "tata steel", "hindalco", "jsw"],
    "Macro / Policy": ["rbi", "sebi", "budget", "gdp", "inflation", "cpi", "wpi", "fiscal deficit", "fii", "dii"],
}

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_trf")
        except OSError:
            logger.warning("en_core_web_trf not found, falling back to en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
    return _nlp


@dataclass
class ExtractedEntity:
    text: str
    canonical: str
    entity_type: str  # ORG, PERSON, GPE, TICKER, INDEX, MACRO
    sectors: list[str] = field(default_factory=list)
    confidence: float = 1.0
    char_start: int = 0
    char_end: int = 0


def extract_entities(text: str) -> list[ExtractedEntity]:
    if not text or not text.strip():
        return []

    entities: list[ExtractedEntity] = []
    nlp = _get_nlp()
    doc = nlp(text[:10_000])  # cap for performance

    seen: set[str] = set()

    # spaCy NER pass
    for ent in doc.ents:
        if ent.label_ not in ("ORG", "PERSON", "GPE", "MONEY", "PRODUCT"):
            continue
        canonical = _resolve_alias(ent.text)
        if canonical in seen:
            continue
        seen.add(canonical)
        entities.append(ExtractedEntity(
            text=ent.text,
            canonical=canonical,
            entity_type=ent.label_,
            sectors=_resolve_sectors(canonical),
            char_start=ent.start_char,
            char_end=ent.end_char,
        ))

    # Ticker regex pass (catches NSE tickers missed by spaCy)
    for match in re.finditer(r"\b([A-Z]{2,10})\b", text):
        ticker = match.group(1)
        if ticker in TICKER_ALIASES and ticker not in seen:
            canonical = TICKER_ALIASES[ticker]
            seen.add(ticker)
            entities.append(ExtractedEntity(
                text=ticker,
                canonical=canonical,
                entity_type="TICKER",
                sectors=_resolve_sectors(canonical),
                char_start=match.start(),
                char_end=match.end(),
            ))

    return entities


def _resolve_alias(text: str) -> str:
    upper = text.upper().strip()
    if upper in TICKER_ALIASES:
        return TICKER_ALIASES[upper]
    for colloquial, canonical in COLLOQUIAL_MAP.items():
        if colloquial.lower() in text.lower():
            return canonical
    return text.strip()


def _resolve_sectors(entity_name: str) -> list[str]:
    lower = entity_name.lower()
    matched = []
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            matched.append(sector)
    return matched or ["General Market"]
