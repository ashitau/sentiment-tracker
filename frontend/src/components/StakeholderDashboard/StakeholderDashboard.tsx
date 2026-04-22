/**
 * Non-technical stakeholder view.
 * All numbers are contextualised in plain English.
 * No jargon, no raw model scores — just signal quality, confidence, and narrative.
 */
import { motion } from "framer-motion";
import { CheckCircle, AlertTriangle, Clock, Globe, TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { ValidationMetrics, EntitySignal } from "../../types";

interface Props {
  validation: ValidationMetrics;
  topSignals: EntitySignal[];
}

export default function StakeholderDashboard({ validation, topSignals }: Props) {
  return (
    <div className="flex flex-col gap-5 h-full overflow-y-auto pr-1">
      <SystemHealthBanner validation={validation} />
      <ReliabilityCard validation={validation} />
      <TopStoriesCard signals={topSignals} />
      <TrackRecordCard validation={validation} />
    </div>
  );
}

function SystemHealthBanner({ validation }: { validation: ValidationMetrics }) {
  const qualityConfig = {
    Strong:   { icon: CheckCircle,    color: "text-green-400",  bg: "bg-green-400/10 border-green-400/30",  headline: "Signal quality is strong — suitable for directional inference." },
    Moderate: { icon: AlertTriangle,  color: "text-amber-400",  bg: "bg-amber-400/10 border-amber-400/30",  headline: "Signal quality is moderate — use alongside other indicators." },
    Weak:     { icon: AlertTriangle,  color: "text-red-400",    bg: "bg-red-400/10 border-red-400/30",      headline: "Limited data — treat signals as exploratory only." },
  }[validation.overall_signal_quality];

  const Icon = qualityConfig.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
      className={`flex items-start gap-3 rounded-xl border p-4 ${qualityConfig.bg}`}
    >
      <Icon className={`mt-0.5 flex-shrink-0 ${qualityConfig.color}`} size={20} />
      <div>
        <p className={`font-semibold text-sm ${qualityConfig.color}`}>{qualityConfig.headline}</p>
        <p className="text-gray-400 text-xs mt-1">{validation.window_label} · Updated {validation.data_freshness_minutes} min ago</p>
      </div>
    </motion.div>
  );
}

function ReliabilityCard({ validation }: { validation: ValidationMetrics }) {
  const metrics = [
    {
      label: "Documents analysed",
      value: validation.total_documents_processed.toLocaleString(),
      sub: validation.data_coverage_label,
      icon: "📄",
      what: "Total posts, comments, and search trends processed. More documents = more reliable signals.",
      threshold: validation.total_documents_processed >= 500 ? "green" : validation.total_documents_processed >= 150 ? "amber" : "red",
    },
    {
      label: "Data freshness",
      value: validation.freshness_label,
      sub: null,
      icon: "⏱",
      what: "How recently data was collected. Under 15 minutes is ideal for live market use.",
      threshold: validation.data_freshness_minutes < 15 ? "green" : validation.data_freshness_minutes < 60 ? "amber" : "red",
    },
    {
      label: "India focus",
      value: `${validation.india_mention_pct}%`,
      sub: validation.india_coverage_label,
      icon: "🇮🇳",
      what: "Percentage of signals originating from Indian users. Higher = more relevant to NSE/BSE.",
      threshold: validation.india_mention_pct >= 60 ? "green" : validation.india_mention_pct >= 30 ? "amber" : "red",
    },
    {
      label: "Entities detected",
      value: validation.total_entities_detected.toString(),
      sub: `across ${validation.total_topics_found} narrative themes`,
      icon: "🔍",
      what: "Distinct companies, indices, or policy topics with measurable sentiment.",
      threshold: validation.total_entities_detected >= 10 ? "green" : validation.total_entities_detected >= 5 ? "amber" : "red",
    },
  ];

  const thresholdColors = {
    green: "border-green-500/40 bg-green-500/5",
    amber: "border-amber-500/40 bg-amber-500/5",
    red:   "border-red-500/40 bg-red-500/5",
  };

  return (
    <div className="rounded-xl border border-brand-border bg-brand-panel p-4">
      <h3 className="text-sm font-semibold text-gray-200 mb-3">How reliable is this data?</h3>
      <div className="grid grid-cols-2 gap-3">
        {metrics.map(m => (
          <motion.div
            key={m.label}
            whileHover={{ scale: 1.01 }}
            className={`rounded-lg border p-3 ${thresholdColors[m.threshold as keyof typeof thresholdColors]}`}
            title={m.what}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <span>{m.icon}</span>
              <span className="text-gray-400 text-xs">{m.label}</span>
            </div>
            <div className="text-white font-semibold text-sm leading-tight">{m.value}</div>
            {m.sub && <div className="text-gray-500 text-xs mt-0.5 leading-tight">{m.sub}</div>}
          </motion.div>
        ))}
      </div>
      <p className="text-gray-500 text-xs mt-3 leading-relaxed">{validation.reliability_summary}</p>
    </div>
  );
}

function TopStoriesCard({ signals }: { signals: EntitySignal[] }) {
  const top5 = signals.slice(0, 5);

  return (
    <div className="rounded-xl border border-brand-border bg-brand-panel p-4">
      <h3 className="text-sm font-semibold text-gray-200 mb-3">What is the market talking about?</h3>
      <div className="flex flex-col gap-2">
        {top5.map((sig, i) => (
          <SignalRow key={sig.canonical_name} signal={sig} rank={i + 1} />
        ))}
      </div>
    </div>
  );
}

function SignalRow({ signal, rank }: { signal: EntitySignal; rank: number }) {
  const DirectionIcon =
    signal.sentiment_direction === 1 ? TrendingUp :
    signal.sentiment_direction === -1 ? TrendingDown : Minus;

  const dirColor =
    signal.sentiment_direction === 1 ? "text-green-400" :
    signal.sentiment_direction === -1 ? "text-red-400" : "text-gray-400";

  const strengthDot =
    signal.signal_strength === "Strong"   ? "bg-green-400" :
    signal.signal_strength === "Moderate" ? "bg-amber-400" : "bg-gray-500";

  const confidencePill =
    signal.confidence_tier === "High"   ? "tier-high" :
    signal.confidence_tier === "Medium" ? "tier-medium" : "tier-low";

  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
      transition={{ delay: rank * 0.05 }}
      className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] border border-transparent hover:border-brand-border transition-colors"
    >
      <span className="text-gray-600 text-xs font-mono mt-0.5 w-4 flex-shrink-0">{rank}</span>
      <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${strengthDot}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-white text-sm font-medium">{signal.canonical_name}</span>
          <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${confidencePill}`}>
            {signal.confidence_tier} confidence
          </span>
        </div>
        <p className="text-gray-400 text-xs mt-1 leading-relaxed line-clamp-2">{signal.plain_summary}</p>
        <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
          <span>{signal.mention_count.toLocaleString()} mentions</span>
          <span>·</span>
          <span>{signal.sectors[0]}</span>
        </div>
      </div>
      <div className={`flex items-center gap-1 flex-shrink-0 ${dirColor}`}>
        <DirectionIcon size={15} />
        <span className="text-xs font-medium">{signal.sentiment_plain_label}</span>
      </div>
    </motion.div>
  );
}

function TrackRecordCard({ validation }: { validation: ValidationMetrics }) {
  const hasHistory = validation.historical_accuracy_pct !== null;

  return (
    <div className="rounded-xl border border-brand-border bg-brand-panel p-4">
      <h3 className="text-sm font-semibold text-gray-200 mb-2">Track record</h3>
      {hasHistory ? (
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{validation.historical_accuracy_pct}%</div>
            <div className="text-gray-500 text-xs">of past signals preceded a measurable price move</div>
          </div>
          <div className="flex-1 text-gray-400 text-xs leading-relaxed">
            <p>{validation.accuracy_label}</p>
            <p className="mt-1 text-gray-500">Based on {validation.total_signals_tracked} signals tracked since system launch.</p>
          </div>
        </div>
      ) : (
        <div className="flex items-start gap-3 text-gray-400">
          <Clock size={16} className="mt-0.5 flex-shrink-0 text-gray-500" />
          <p className="text-xs leading-relaxed">
            Track record will populate automatically after the system accumulates 30+ days of signal history.
            Once available, you'll see what percentage of past high-confidence signals preceded a measurable
            market move — giving this tool a verifiable, quantitative credibility score.
          </p>
        </div>
      )}
    </div>
  );
}
