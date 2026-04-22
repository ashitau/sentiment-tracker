import { motion, AnimatePresence } from "framer-motion";
import { X, TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { EntitySignal } from "../../types";

interface Props {
  signal: EntitySignal | null;
  onClose: () => void;
}

export default function SignalDetailPanel({ signal, onClose }: Props) {
  return (
    <AnimatePresence>
      {signal && (
        <motion.div
          key={signal.canonical_name}
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 40 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="absolute right-0 top-0 bottom-0 w-80 bg-brand-panel border-l border-brand-border overflow-y-auto z-20 flex flex-col"
        >
          {/* Header */}
          <div className="flex items-start justify-between p-4 border-b border-brand-border">
            <div>
              <h3 className="text-white font-semibold">{signal.canonical_name}</h3>
              <p className="text-gray-500 text-xs mt-0.5">{signal.sectors.join(" · ")}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-white transition-colors ml-2 flex-shrink-0"
            >
              <X size={16} />
            </button>
          </div>

          <div className="flex flex-col gap-4 p-4 flex-1">
            {/* Plain summary */}
            <div className="rounded-lg bg-white/[0.03] border border-brand-border p-3">
              <p className="text-gray-300 text-sm leading-relaxed">{signal.plain_summary}</p>
            </div>

            {/* Signal scores — human-readable */}
            <div>
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Signal breakdown</h4>
              <div className="flex flex-col gap-2">
                <ScoreRow label="How often it's mentioned" value={signal.frequency_score} description="Frequency above baseline" />
                <ScoreRow label="India relevance" value={signal.geography_score} description="Share of India-origin signals" />
                <ScoreRow label="Market relevance" value={signal.sector_score} description="Proximity to key NSE sectors" />
                <ScoreRow label="Source quality" value={signal.credibility_score} description="Weighted by source credibility" />
              </div>
            </div>

            {/* Sentiment */}
            <div>
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Sentiment</h4>
              <SentimentBlock signal={signal} />
            </div>

            {/* Sample quotes */}
            {signal.sample_texts.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Sample quotes</h4>
                <div className="flex flex-col gap-2">
                  {signal.sample_texts.map((text, i) => (
                    <p key={i} className="text-gray-400 text-xs leading-relaxed italic border-l-2 border-brand-border pl-2">
                      "{text.slice(0, 180)}{text.length > 180 ? "…" : ""}"
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Confidence explanation */}
            <div className="rounded-lg bg-white/[0.02] border border-brand-border p-3 mt-auto">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400">Overall confidence</span>
                <ConfidencePill tier={signal.confidence_tier} />
              </div>
              <p className="text-gray-500 text-xs leading-relaxed">
                {signal.confidence_tier === "High"
                  ? `${signal.mention_count}+ mentions from multiple sources — signal is well-supported.`
                  : signal.confidence_tier === "Medium"
                  ? "Moderate evidence — directionally useful, but corroborate with other data."
                  : "Early signal with limited data. Monitor for confirmation before drawing conclusions."}
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function ScoreRow({ label, value }: { label: string; value: number; description: string }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-amber-500" : "bg-gray-600";

  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-300">{label}</span>
        <span className="text-gray-500">{pct}%</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-gray-800 rounded-full h-1.5">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6 }}
            className={`h-1.5 rounded-full ${color}`}
          />
        </div>
      </div>
    </div>
  );
}

function SentimentBlock({ signal }: { signal: EntitySignal }) {
  const Icon = signal.sentiment_direction === 1 ? TrendingUp : signal.sentiment_direction === -1 ? TrendingDown : Minus;
  const color = signal.sentiment_direction === 1 ? "text-green-400 bg-green-400/10 border-green-400/30" :
                signal.sentiment_direction === -1 ? "text-red-400 bg-red-400/10 border-red-400/30" :
                "text-gray-400 bg-gray-400/10 border-gray-400/30";

  return (
    <div className={`flex items-center gap-3 rounded-lg border p-3 ${color}`}>
      <Icon size={20} />
      <div>
        <div className="font-semibold text-sm">{signal.sentiment_plain_label}</div>
        <div className="text-xs opacity-70">
          Strength: {Math.round(signal.sentiment_magnitude * 100)}% · {signal.mention_count} data points
        </div>
      </div>
    </div>
  );
}

function ConfidencePill({ tier }: { tier: string }) {
  const cls = tier === "High" ? "tier-high" : tier === "Medium" ? "tier-medium" : "tier-low";
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{tier}</span>;
}
