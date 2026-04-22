/**
 * Validation metrics panel — dual layer:
 *   Top row: plain-English indicators for stakeholders
 *   Bottom: source breakdown for technical users
 */
import { motion } from "framer-motion";
import type { ValidationMetrics } from "../../types";

interface Props {
  validation: ValidationMetrics;
}

export default function ValidationPanel({ validation }: Props) {
  return (
    <div className="rounded-xl border border-brand-border bg-brand-panel p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-200">Data Reliability</h3>
        <QualityBadge quality={validation.overall_signal_quality} />
      </div>

      <div className="grid grid-cols-4 gap-3 mb-4">
        <StatTile
          emoji="📄"
          label="Docs analysed"
          value={validation.total_documents_processed.toLocaleString()}
          sub={validation.data_coverage_label}
          color={validation.total_documents_processed >= 500 ? "green" : validation.total_documents_processed >= 150 ? "amber" : "red"}
        />
        <StatTile
          emoji="⏱"
          label="Data age"
          value={
            validation.data_freshness_minutes < 60
              ? `${validation.data_freshness_minutes}m`
              : `${Math.round(validation.data_freshness_minutes / 60)}h`
          }
          sub={validation.freshness_label}
          color={validation.data_freshness_minutes < 15 ? "green" : validation.data_freshness_minutes < 60 ? "amber" : "red"}
        />
        <StatTile
          emoji="🇮🇳"
          label="India signals"
          value={`${validation.india_mention_pct}%`}
          sub={validation.india_mention_pct >= 60 ? "Strongly focused" : "Partial coverage"}
          color={validation.india_mention_pct >= 60 ? "green" : validation.india_mention_pct >= 30 ? "amber" : "red"}
        />
        <StatTile
          emoji="🔍"
          label="Entities"
          value={validation.total_entities_detected.toString()}
          sub={`${validation.total_topics_found} themes`}
          color={validation.total_entities_detected >= 10 ? "green" : "amber"}
        />
      </div>

      {/* Source breakdown bar */}
      <div>
        <p className="text-xs text-gray-500 mb-2">Source mix</p>
        <SourceBar breakdown={validation.source_breakdown} total={validation.total_documents_processed} />
      </div>
    </div>
  );
}

function QualityBadge({ quality }: { quality: string }) {
  const config = {
    Strong:   { dot: "bg-green-400", text: "text-green-400", label: "Strong signal" },
    Moderate: { dot: "bg-amber-400", text: "text-amber-400", label: "Moderate signal" },
    Weak:     { dot: "bg-red-400",   text: "text-red-400",   label: "Limited signal" },
  }[quality] ?? { dot: "bg-gray-400", text: "text-gray-400", label: quality };

  return (
    <div className={`flex items-center gap-1.5 text-xs font-medium ${config.text}`}>
      <div className={`w-2 h-2 rounded-full ${config.dot} animate-pulse`} />
      {config.label}
    </div>
  );
}

function StatTile({
  emoji, label, value, sub, color,
}: {
  emoji: string; label: string; value: string; sub: string; color: "green" | "amber" | "red";
}) {
  const borderColors = {
    green: "border-green-500/30 bg-green-500/5",
    amber: "border-amber-500/30 bg-amber-500/5",
    red:   "border-red-500/30 bg-red-500/5",
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className={`rounded-lg border p-3 ${borderColors[color]}`}
    >
      <div className="text-lg mb-1">{emoji}</div>
      <div className="text-white font-bold text-sm">{value}</div>
      <div className="text-gray-500 text-xs mt-0.5 truncate" title={sub}>{sub}</div>
      <div className="text-gray-600 text-xs mt-1">{label}</div>
    </motion.div>
  );
}

function SourceBar({ breakdown, total }: { breakdown: Record<string, number>; total: number }) {
  const sourceColors: Record<string, string> = {
    reddit:        "#ff4500",
    google_trends: "#4285f4",
    news_rss:      "#10b981",
    telegram:      "#0088cc",
    twitter:       "#1d9bf0",
  };

  const entries = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);

  return (
    <div>
      <div className="flex h-2 rounded-full overflow-hidden gap-0.5 mb-2">
        {entries.map(([src, count]) => (
          <motion.div
            key={src}
            initial={{ width: 0 }}
            animate={{ width: `${(count / total) * 100}%` }}
            transition={{ duration: 0.8 }}
            className="h-full rounded-full"
            style={{ backgroundColor: sourceColors[src] ?? "#6b7280" }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        {entries.map(([src, count]) => (
          <div key={src} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: sourceColors[src] ?? "#6b7280" }} />
            <span className="text-gray-400 text-xs capitalize">{src.replace("_", " ")}</span>
            <span className="text-gray-600 text-xs">({((count / total) * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}
