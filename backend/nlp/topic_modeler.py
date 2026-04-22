"""
BERTopic-based topic modelling.
Groups posts into narrative clusters without manual label creation.
"""
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from loguru import logger

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MIN_TOPIC_SIZE = 5


@dataclass
class TopicCluster:
    topic_id: int
    label: str                      # auto-generated keyword summary
    keywords: list[tuple[str, float]]  # (word, relevance_score)
    document_count: int
    representative_docs: list[str]
    sectors: list[str] = field(default_factory=list)
    trend_velocity: float = 0.0    # change in doc count vs. previous window
    plain_label: str = ""          # stakeholder-friendly name


_model: Optional[BERTopic] = None
_embedder: Optional[SentenceTransformer] = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        logger.info(f"Loading sentence embedder: {EMBEDDING_MODEL}")
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def fit_topics(documents: list[str], timestamps: Optional[list] = None) -> tuple[BERTopic, list[int], np.ndarray]:
    """
    Fit BERTopic on a corpus of documents.
    Returns (model, topic_assignments, embeddings).
    """
    global _model
    embedder = _get_embedder()

    logger.info(f"Fitting BERTopic on {len(documents)} documents")
    embeddings = embedder.encode(documents, show_progress_bar=True, batch_size=64)

    topic_model = BERTopic(
        embedding_model=embedder,
        min_topic_size=MIN_TOPIC_SIZE,
        calculate_probabilities=False,
        verbose=False,
    )

    topics, _ = topic_model.fit_transform(documents, embeddings)
    _model = topic_model
    logger.info(f"BERTopic found {len(topic_model.get_topic_info()) - 1} topics (excl. outlier topic)")
    return topic_model, topics, embeddings


def extract_topic_clusters(
    topic_model: BERTopic,
    documents: list[str],
    topic_assignments: list[int],
) -> list[TopicCluster]:
    clusters = []
    info_df = topic_model.get_topic_info()

    for _, row in info_df.iterrows():
        topic_id = int(row["Topic"])
        if topic_id == -1:
            continue  # outlier cluster

        keywords = topic_model.get_topic(topic_id) or []
        doc_indices = [i for i, t in enumerate(topic_assignments) if t == topic_id]
        rep_docs = [documents[i] for i in doc_indices[:3]]

        kw_strings = [kw for kw, _ in keywords[:5]]
        auto_label = " · ".join(kw_strings[:3])
        plain_label = _humanise_label(kw_strings)

        clusters.append(TopicCluster(
            topic_id=topic_id,
            label=auto_label,
            keywords=keywords[:10],
            document_count=len(doc_indices),
            representative_docs=rep_docs,
            plain_label=plain_label,
        ))

    return sorted(clusters, key=lambda c: c.document_count, reverse=True)


def _humanise_label(keywords: list[str]) -> str:
    """
    Convert raw BERTopic keyword list to a readable narrative label.
    e.g. ['rate', 'rbi', 'repo', 'cut'] → 'RBI Rate Action'
    """
    kw_lower = [k.lower() for k in keywords]

    label_rules = [
        (["rbi", "repo", "rate", "cut", "hike"],  "RBI Rate Action"),
        (["sebi", "regulation", "rule", "circular"], "SEBI Regulatory Update"),
        (["ipo", "listing", "grey market", "gmp"],  "IPO Activity"),
        (["earnings", "results", "profit", "revenue", "quarter"], "Quarterly Earnings"),
        (["fii", "dii", "foreign", "institutional", "sell", "buy"], "Institutional Flow"),
        (["budget", "fiscal", "tax", "finance minister"], "Budget / Fiscal Policy"),
        (["crash", "fall", "drop", "correction", "bear"], "Market Correction Concern"),
        (["rally", "surge", "bull", "breakout", "high"],  "Bullish Market Momentum"),
        (["it", "tech", "software", "layoff", "hiring"],  "IT Sector Development"),
        (["bank", "npa", "loan", "credit", "nbfc"],       "Banking Sector Update"),
    ]

    for trigger_words, label in label_rules:
        if any(t in kw_lower for t in trigger_words):
            return label

    return " ".join(w.capitalize() for w in keywords[:3]) + " Trend"
