import time
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
from pytrends.request import TrendReq
from loguru import logger

SECTOR_KEYWORD_GROUPS = {
    "banking": ["HDFC Bank", "SBI", "ICICI Bank", "RBI rate", "banking sector"],
    "it": ["Infosys", "TCS", "Wipro", "IT sector India", "tech layoffs India"],
    "energy": ["Reliance Industries", "ONGC", "oil price India", "green energy India"],
    "auto": ["Tata Motors", "Maruti", "EV India", "auto sector"],
    "pharma": ["Sun Pharma", "Dr Reddy", "pharma India", "USFDA"],
    "fmcg": ["HUL", "ITC", "FMCG India", "consumer inflation"],
    "realty": ["DLF", "real estate India", "housing loan", "property prices"],
    "market": ["NIFTY 50", "SENSEX", "stock market India", "FII selling", "market crash India"],
}

GEO_INDIA = "IN"
GEO_CITIES = ["IN-DL", "IN-MH", "IN-KA", "IN-TN", "IN-GJ"]  # Delhi, Mumbai, Bangalore, Chennai, Ahmedabad


def _build_client(timeout: int = 10) -> TrendReq:
    return TrendReq(hl="en-IN", tz=330, timeout=(timeout, timeout), retries=2, backoff_factor=0.5)


def fetch_sector_trends(
    timeframe: str = "now 1-d",
    geo: str = GEO_INDIA,
) -> dict[str, pd.DataFrame]:
    """Return interest-over-time DataFrames keyed by sector."""
    pytrends = _build_client()
    results: dict[str, pd.DataFrame] = {}

    for sector, keywords in SECTOR_KEYWORD_GROUPS.items():
        try:
            pytrends.build_payload(keywords[:5], timeframe=timeframe, geo=geo)
            df = pytrends.interest_over_time()
            if not df.empty:
                df["sector"] = sector
                df["fetched_at"] = datetime.now(tz=timezone.utc).isoformat()
                results[sector] = df
                logger.debug(f"Trends fetched: {sector} ({len(df)} rows)")
            time.sleep(1.2)  # stay well under rate limits
        except Exception as exc:
            logger.warning(f"Trends failed for sector '{sector}': {exc}")

    return results


def fetch_related_queries(keywords: list[str], geo: str = GEO_INDIA) -> dict[str, list[str]]:
    """Return top related queries for a list of keywords — useful for discovering emerging narratives."""
    pytrends = _build_client()
    related: dict[str, list[str]] = {}

    for i in range(0, len(keywords), 5):
        batch = keywords[i : i + 5]
        try:
            pytrends.build_payload(batch, timeframe="now 7-d", geo=geo)
            rq = pytrends.related_queries()
            for kw in batch:
                top = rq.get(kw, {}).get("top")
                if top is not None and not top.empty:
                    related[kw] = top["query"].tolist()
            time.sleep(1.5)
        except Exception as exc:
            logger.warning(f"Related queries failed for batch {batch}: {exc}")

    return related


def fetch_geo_breakdown(keyword: str, resolution: str = "CITY") -> Optional[pd.DataFrame]:
    """Return per-city interest scores for a single keyword — feeds the geography weight."""
    pytrends = _build_client()
    try:
        pytrends.build_payload([keyword], timeframe="now 7-d", geo=GEO_INDIA)
        df = pytrends.interest_by_region(resolution=resolution, inc_low_vol=True)
        df = df[df[keyword] > 0].sort_values(keyword, ascending=False)
        df["keyword"] = keyword
        df["fetched_at"] = datetime.now(tz=timezone.utc).isoformat()
        return df
    except Exception as exc:
        logger.warning(f"Geo breakdown failed for '{keyword}': {exc}")
        return None


def trends_to_documents(sector_df_map: dict[str, pd.DataFrame]) -> list[dict]:
    """Flatten trend DataFrames into storable documents (one per keyword-timestamp)."""
    docs = []
    for sector, df in sector_df_map.items():
        for ts, row in df.iterrows():
            for col in df.columns:
                if col in ("isPartial", "sector", "fetched_at"):
                    continue
                docs.append({
                    "source": "google_trends",
                    "source_type": "trend_datapoint",
                    "keyword": col,
                    "sector": sector,
                    "interest_score": int(row[col]),
                    "timestamp": ts.isoformat(),
                    "fetched_at": row["fetched_at"],
                    "geo": GEO_INDIA,
                    "is_partial": bool(row.get("isPartial", False)),
                })
    return docs
