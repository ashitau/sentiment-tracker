export interface EntitySignal {
  canonical_name: string;
  sectors: string[];
  mention_count: number;
  total_reach: number;
  composite_score: number;
  frequency_score: number;
  geography_score: number;
  sector_score: number;
  credibility_score: number;
  sentiment_direction: -1 | 0 | 1;
  sentiment_label: "positive" | "negative" | "neutral";
  sentiment_plain_label: string;
  sentiment_magnitude: number;
  signal_strength: "Strong" | "Moderate" | "Emerging";
  confidence_tier: "High" | "Medium" | "Low";
  plain_summary: string;
  sample_texts: string[];
  sources: string[];
  first_seen: string | null;
  last_seen: string | null;
}

export interface TopicCluster {
  topic_id: number;
  label: string;
  plain_label: string;
  keywords: [string, number][];
  document_count: number;
  representative_docs: string[];
  sectors: string[];
  trend_velocity: number;
}

export interface ValidationMetrics {
  window_label: string;
  total_documents_processed: number;
  total_entities_detected: number;
  total_topics_found: number;
  data_freshness_minutes: number;
  source_breakdown: Record<string, number>;
  india_mention_pct: number;
  overall_signal_quality: "Strong" | "Moderate" | "Weak";
  data_coverage_label: "Comprehensive" | "Partial" | "Limited";
  freshness_label: string;
  india_coverage_label: string;
  reliability_summary: string;
  signals_that_preceded_moves: number | null;
  total_signals_tracked: number | null;
  historical_accuracy_pct: number | null;
  accuracy_label: string | null;
}

export interface KeywordNode {
  word: string;
  weight: number;
  mention_count: number;
  sector: string;
  sentiment: string;
  direction: -1 | 0 | 1;
  signal_strength: "Strong" | "Moderate" | "Emerging";
}

export interface SectorHeatmapEntry {
  score: number;
  direction: number;
  mention_count: number;
  plain_label: string;
}

export interface DashboardSnapshot {
  generated_at: string;
  top_signals: EntitySignal[];
  topic_clusters: TopicCluster[];
  validation: ValidationMetrics;
  trending_keywords: KeywordNode[];
  sector_heatmap: Record<string, SectorHeatmapEntry>;
}
