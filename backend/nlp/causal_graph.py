"""
Causal Knowledge Graph for India market linkages.

Maps consumer/macro topics → commodities → listed entities via supply chain
relationships. Used by the weak signal detector to filter noise: only topics
with a credible causal path (≤3 hops) to a market entity get surfaced.

Hop scoring:
  1 hop (direct)  → causal_score 0.90
  2 hops          → causal_score 0.65
  3 hops          → causal_score 0.40
  >3 hops         → filtered out (score < threshold)

Node types: TOPIC, COMMODITY, SECTOR, ENTITY (listed company/index)
Edge attributes: relationship, strength (0-1)
"""
import re
from dataclasses import dataclass, field
from typing import Optional
import networkx as nx


@dataclass
class CausalPath:
    topic: str
    hops: list[str]                  # full path from topic → listed entity
    market_entity: str               # terminal market-relevant node
    affected_sector: str
    causal_score: float              # 0-1, decays with hop count
    relationship_chain: list[str]    # human-readable edge labels
    plain_explanation: str           # "X → Y because Z"


def _score(hops: int) -> float:
    return {1: 0.90, 2: 0.65, 3: 0.40}.get(hops, 0.0)


def build_india_causal_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    # ── Node helper ──────────────────────────────────────────────────────────
    def add(node: str, ntype: str, **attrs):
        G.add_node(node, node_type=ntype, **attrs)

    def link(src: str, dst: str, rel: str, strength: float = 0.8):
        G.add_edge(src, dst, relationship=rel, strength=strength)

    # ── COMMODITIES ──────────────────────────────────────────────────────────
    for c in ["aluminium", "steel", "crude oil", "natural gas", "coal",
              "copper", "vegetable oil", "wheat", "sugar", "rubber",
              "lithium", "rare earth", "urea", "phosphate", "cotton",
              "palm oil", "soybean", "gold", "silver", "zinc"]:
        add(c, "COMMODITY")

    # ── SECTORS ──────────────────────────────────────────────────────────────
    for s in ["Metals & Mining", "Energy", "FMCG", "Automobile", "Pharmaceuticals",
              "Banking & Finance", "Information Technology", "Fertilizers",
              "Textiles", "Aviation", "Real Estate", "Power", "Chemicals"]:
        add(s, "SECTOR")

    # ── LISTED ENTITIES ──────────────────────────────────────────────────────
    entities = {
        "Hindalco":            "Metals & Mining",
        "National Aluminium":  "Metals & Mining",
        "Tata Steel":          "Metals & Mining",
        "JSW Steel":           "Metals & Mining",
        "Coal India":          "Metals & Mining",
        "Vedanta":             "Metals & Mining",
        "Hindustan Zinc":      "Metals & Mining",
        "ONGC":                "Energy",
        "Reliance Industries": "Energy",
        "HPCL":                "Energy",
        "BPCL":                "Energy",
        "IOC":                 "Energy",
        "Adani Green":         "Energy",
        "NTPC":                "Power",
        "Power Grid":          "Power",
        "Adani Power":         "Power",
        "HUL":                 "FMCG",
        "Adani Wilmar":        "FMCG",
        "Ruchi Soya":          "FMCG",
        "Britannia":           "FMCG",
        "Nestle India":        "FMCG",
        "Dabur":               "FMCG",
        "Marico":              "FMCG",
        "Tata Motors":         "Automobile",
        "Maruti Suzuki":       "Automobile",
        "Bajaj Auto":          "Automobile",
        "Hero MotoCorp":       "Automobile",
        "Motherson Sumi":      "Automobile",
        "Apollo Tyres":        "Automobile",
        "Coromandel International": "Fertilizers",
        "Chambal Fertilisers": "Fertilizers",
        "Rashtriya Chemicals": "Fertilizers",
        "Indigo":              "Aviation",
        "SpiceJet":            "Aviation",
        "Asian Paints":        "Chemicals",
        "Berger Paints":       "Chemicals",
        "Pidilite":            "Chemicals",
        "Sun Pharmaceutical":  "Pharmaceuticals",
        "Dr Reddy's":          "Pharmaceuticals",
        "Cipla":               "Pharmaceuticals",
        "Infosys":             "Information Technology",
        "TCS":                 "Information Technology",
        "Wipro":               "Information Technology",
        "DLF":                 "Real Estate",
        "Oberoi Realty":       "Real Estate",
        "Welspun India":       "Textiles",
        "Vardhman Textiles":   "Textiles",
    }
    for entity, sector in entities.items():
        add(entity, "ENTITY", sector=sector)
        link(sector, entity, "contains", strength=1.0)

    # ── COMMODITY → SECTOR linkages ──────────────────────────────────────────
    comm_sector = [
        ("aluminium",   "Metals & Mining", "primary input"),
        ("steel",       "Metals & Mining", "primary input"),
        ("steel",       "Automobile",      "body & chassis input", 0.7),
        ("steel",       "Real Estate",     "construction input", 0.6),
        ("crude oil",   "Energy",          "primary commodity"),
        ("crude oil",   "Chemicals",       "petrochemical feedstock", 0.75),
        ("crude oil",   "Aviation",        "ATF cost driver", 0.85),
        ("crude oil",   "Automobile",      "fuel cost sentiment", 0.5),
        ("natural gas", "Energy",          "feedstock"),
        ("natural gas", "Fertilizers",     "urea feedstock", 0.9),
        ("natural gas", "Power",           "gas-based generation", 0.7),
        ("coal",        "Power",           "thermal generation input", 0.95),
        ("coal",        "Metals & Mining", "coking coal for steel", 0.8),
        ("copper",      "Metals & Mining", "primary metal"),
        ("copper",      "Information Technology", "electronics demand proxy", 0.5),
        ("vegetable oil","FMCG",           "edible oil input", 0.9),
        ("palm oil",    "FMCG",            "edible oil input", 0.85),
        ("soybean",     "FMCG",            "edible oil & protein input", 0.75),
        ("wheat",       "FMCG",            "flour & food input", 0.85),
        ("sugar",       "FMCG",            "primary food input", 0.8),
        ("urea",        "Fertilizers",     "primary product", 0.9),
        ("phosphate",   "Fertilizers",     "DAP input", 0.85),
        ("rubber",      "Automobile",      "tyre input", 0.9),
        ("lithium",     "Automobile",      "EV battery input", 0.85),
        ("lithium",     "Information Technology", "battery supply chain", 0.6),
        ("rare earth",  "Information Technology", "semiconductor supply chain", 0.7),
        ("cotton",      "Textiles",        "primary fibre input", 0.95),
        ("gold",        "Banking & Finance","MCX & jewellery demand proxy", 0.65),
        ("zinc",        "Metals & Mining", "primary metal", 0.9),
    ]
    for row in comm_sector:
        link(row[0], row[1], row[2], row[3] if len(row) > 3 else 0.8)

    # ── TOPIC NODES — consumer / macro trigger terms ─────────────────────────
    # These are what get detected from broad ingestion.
    # Format: (topic_term, commodity/sector, relationship_label, strength)
    consumer_topics = [
        # Beverages / packaging
        ("aluminium can shortage",  "aluminium",    "packaging demand", 0.9),
        ("can shortage",            "aluminium",    "packaging demand", 0.85),
        ("diet coke shortage",      "aluminium",    "beverage can demand", 0.75),
        ("beverage shortage",       "aluminium",    "packaging demand", 0.7),
        ("beer shortage",           "aluminium",    "can packaging demand", 0.7),

        # Fuel / energy
        ("petrol price hike",       "crude oil",    "downstream retail price", 0.9),
        ("diesel price rise",       "crude oil",    "downstream retail price", 0.9),
        ("cng shortage",            "natural gas",  "city gas distribution", 0.85),
        ("lpg shortage",            "crude oil",    "LPG supply chain", 0.8),
        ("power cut",               "coal",         "thermal demand surge", 0.85),
        ("electricity outage",      "coal",         "thermal demand proxy", 0.8),
        ("load shedding",           "coal",         "thermal demand proxy", 0.8),

        # Food / agri
        ("onion price rise",        "FMCG",         "food inflation sentiment", 0.7),
        ("tomato shortage",         "FMCG",         "food inflation sentiment", 0.7),
        ("edible oil shortage",     "vegetable oil","direct shortage", 0.9),
        ("wheat shortage",          "wheat",        "flour supply constraint", 0.9),
        ("sugar shortage",          "sugar",        "direct shortage", 0.9),
        ("cooking oil expensive",   "palm oil",     "import cost pressure", 0.8),
        ("food inflation",          "vegetable oil","macro food price signal", 0.75),
        ("dal shortage",            "soybean",      "protein crop proxy", 0.65),

        # Automobiles / EVs
        ("ev charging issue",       "lithium",      "EV adoption friction", 0.7),
        ("petrol car demand",       "crude oil",    "ICE demand persistence", 0.6),
        ("chip shortage cars",      "rare earth",   "semiconductor supply chain", 0.8),
        ("used car prices",         "Automobile",   "new car demand proxy", 0.65),
        ("ola uber strike",         "Automobile",   "mobility demand signal", 0.5),

        # Logistics / supply chain
        ("truck strike",            "steel",        "logistics disruption → capex", 0.55),
        ("port congestion",         "Metals & Mining","import delay signal", 0.65),
        ("container shortage",      "Metals & Mining","import/export cost", 0.6),
        ("shipping freight rise",   "crude oil",    "bunker fuel cost", 0.7),

        # Construction / real estate
        ("cement shortage",         "Real Estate",  "construction input", 0.75),
        ("sand shortage",           "Real Estate",  "construction bottleneck", 0.7),
        ("construction slowdown",   "steel",        "demand decline signal", 0.7),

        # Tech / semiconductors
        ("phone chip shortage",     "rare earth",   "semiconductor demand", 0.75),
        ("ai gpu shortage",         "rare earth",   "data centre demand", 0.7),
        ("smartphone sales drop",   "Information Technology","consumer tech proxy", 0.6),

        # Healthcare / pharma
        ("medicine shortage",       "Pharmaceuticals","direct sector signal", 0.8),
        ("hospital capacity",       "Pharmaceuticals","healthcare demand", 0.65),
        ("paracetamol shortage",    "Pharmaceuticals","API supply chain", 0.85),

        # Banking / macro
        ("upi down",                "Banking & Finance","digital payment infra", 0.7),
        ("atm cash shortage",       "Banking & Finance","liquidity signal", 0.75),
        ("dollar shortage india",   "Banking & Finance","forex reserve signal", 0.8),
        ("rupee fall",              "Banking & Finance","currency macro signal", 0.85),
        ("gold rush india",         "gold",         "safe haven demand", 0.8),

        # Climate / monsoon
        ("drought india",           "wheat",        "crop failure signal", 0.85),
        ("flood damage crops",      "vegetable oil","supply disruption", 0.8),
        ("heatwave power demand",   "coal",         "peak power demand", 0.85),
        ("monsoon delay",           "wheat",        "kharif crop risk", 0.8),
        ("cyclone gujarat",         "Chemicals",    "petrochemical hub disruption", 0.75),

        # Labour / workforce
        ("it layoffs india",        "Information Technology","sector contraction signal", 0.8),
        ("factory workers strike",  "Automobile",   "production stoppage", 0.75),
        ("textile workers protest", "Textiles",     "production disruption", 0.75),
    ]

    for row in consumer_topics:
        topic, target, rel, strength = row
        add(topic, "TOPIC")
        link(topic, target, rel, strength)

    return G


# Singleton
_GRAPH: Optional[nx.DiGraph] = None


def get_graph() -> nx.DiGraph:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_india_causal_graph()
    return _GRAPH


def find_causal_paths(topic_term: str, max_hops: int = 3) -> list[CausalPath]:
    """
    Given a detected trending topic string, find all causal paths to
    market entities within max_hops. Returns empty list if no path found.
    """
    G = get_graph()
    topic_lower = topic_term.lower().strip()

    # Find matching topic nodes (fuzzy match against TOPIC nodes)
    matched_nodes = [
        n for n, d in G.nodes(data=True)
        if d.get("node_type") == "TOPIC" and _fuzzy_match(topic_lower, n)
    ]

    paths: list[CausalPath] = []

    for topic_node in matched_nodes:
        # BFS from topic node to ENTITY nodes
        for entity_node, entity_data in G.nodes(data=True):
            if entity_data.get("node_type") != "ENTITY":
                continue
            try:
                path = nx.shortest_path(G, topic_node, entity_node)
            except nx.NetworkXNoPath:
                continue
            except nx.NodeNotFound:
                continue

            hop_count = len(path) - 1
            if hop_count > max_hops:
                continue

            score = _score(hop_count)
            if score < 0.35:
                continue

            edges = [
                G[path[i]][path[i + 1]].get("relationship", "→")
                for i in range(len(path) - 1)
            ]
            sector = entity_data.get("sector", "General Market")
            explanation = _build_explanation(topic_node, path, edges, entity_node, score)

            paths.append(CausalPath(
                topic=topic_term,
                hops=path,
                market_entity=entity_node,
                affected_sector=sector,
                causal_score=round(score, 3),
                relationship_chain=edges,
                plain_explanation=explanation,
            ))

    # Deduplicate by entity, keep highest score
    best: dict[str, CausalPath] = {}
    for p in paths:
        if p.market_entity not in best or p.causal_score > best[p.market_entity].causal_score:
            best[p.market_entity] = p

    return sorted(best.values(), key=lambda x: x.causal_score, reverse=True)


def _fuzzy_match(query: str, node: str) -> bool:
    """True if any significant word in query appears in node name or vice versa."""
    stopwords = {"in", "is", "a", "the", "of", "and", "or", "india", "indian"}
    q_words = {w for w in re.split(r"\W+", query) if len(w) > 3 and w not in stopwords}
    n_words = {w for w in re.split(r"\W+", node.lower()) if len(w) > 3 and w not in stopwords}
    return bool(q_words & n_words)


def _build_explanation(topic: str, path: list, edges: list, entity: str, score: float) -> str:
    confidence = "directly" if len(path) == 2 else f"via {len(path) - 2} intermediate step{'s' if len(path) > 3 else ''}"
    chain = " → ".join(path[1:])
    confidence_word = "strongly" if score >= 0.8 else ("moderately" if score >= 0.55 else "weakly")
    return (
        f"'{topic.title()}' is {confidence_word} correlated to {entity} ({confidence}). "
        f"Supply chain: {topic} → {chain}. "
        f"Causal confidence: {int(score * 100)}%."
    )
