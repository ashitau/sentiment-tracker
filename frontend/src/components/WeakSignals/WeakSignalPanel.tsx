/**
 * Weak Signal Panel.
 *
 * Surfaces non-financial trending topics that have a credible supply-chain
 * or macro path to a listed entity. Always labelled "Exploratory".
 *
 * Design principles:
 * - Visually distinct from the main constellation (dimmer palette, different iconography)
 * - Causal chain is always shown explicitly — never hide the reasoning
 * - Analysts can promote or dismiss signals
 * - Confidence is never overstated
 */
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Radar, ChevronDown, ChevronRight, ArrowRight, CheckCircle, XCircle, AlertTriangle, Zap } from "lucide-react";
import type { WeakSignal } from "../../types";

interface Props {
  signals: WeakSignal[];
  onPromote?: (signal: WeakSignal) => void;
  onDismiss?: (signal: WeakSignal) => void;
}

const SOURCE_LABELS: Record<string, string> = {
  google_trends_trending: "Google Trending",
  google_trends_rising:   "Google Rising",
  reddit_broad:           "Reddit (Public)",
};

const HOP_COLORS = ["text-green-400", "text-amber-400", "text-orange-400", "text-gray-400"];
const HOP_LABELS = ["Direct", "1 step", "2 steps", "3 steps"];

export default function WeakSignalPanel({ signals, onPromote, onDismiss }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "unreviewed" | "promoted">("unreviewed");

  const filtered = signals.filter(s =>
    filter === "all" ? true :
    filter === "unreviewed" ? s.status === "unreviewed" :
    s.status === "promoted"
  );

  const unreviewedCount = signals.filter(s => s.status === "unreviewed").length;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-brand-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <Radar size={16} className="text-violet-400" />
          <h3 className="text-sm font-semibold text-gray-200">Signals to Watch</h3>
          {unreviewedCount > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-medium">
              {unreviewedCount} new
            </span>
          )}
        </div>
        <div className="flex gap-1 text-xs">
          {(["unreviewed", "promoted", "all"] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 rounded capitalize transition-colors ${
                filter === f ? "bg-violet-500/20 text-violet-300" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Exploratory disclaimer */}
      <div className="mx-4 mt-3 mb-2 flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/8 border border-amber-500/20 flex-shrink-0">
        <AlertTriangle size={12} className="text-amber-400 mt-0.5 flex-shrink-0" />
        <p className="text-amber-300/80 text-xs leading-relaxed">
          These are <strong>exploratory</strong> signals — non-financial topics detected via supply-chain correlation.
          Verify with sector sources before drawing conclusions.
        </p>
      </div>

      {/* Signal list */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 flex flex-col gap-2">
        <AnimatePresence>
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-gray-600 text-sm">
              <Radar size={28} className="mb-2 opacity-30" />
              No {filter} signals at this time.
            </div>
          ) : (
            filtered.map((signal, i) => (
              <WeakSignalCard
                key={signal.raw_topic}
                signal={signal}
                index={i}
                isExpanded={expandedId === signal.raw_topic}
                onToggle={() => setExpandedId(prev => prev === signal.raw_topic ? null : signal.raw_topic)}
                onPromote={onPromote}
                onDismiss={onDismiss}
              />
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function WeakSignalCard({
  signal, index, isExpanded, onToggle, onPromote, onDismiss,
}: {
  signal: WeakSignal;
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
  onPromote?: (s: WeakSignal) => void;
  onDismiss?: (s: WeakSignal) => void;
}) {
  const hopIdx = Math.min(signal.hop_count - 1, 3);
  const hopColor = HOP_COLORS[hopIdx] ?? "text-gray-400";
  const hopLabel = HOP_LABELS[hopIdx] ?? "Distant";

  const burstLabel =
    signal.burst_score >= 0.7 ? "Surging" :
    signal.burst_score >= 0.4 ? "Rising" : "Elevated";
  const burstColor =
    signal.burst_score >= 0.7 ? "text-rose-400" :
    signal.burst_score >= 0.4 ? "text-amber-400" : "text-gray-400";

  const causalPct = Math.round(signal.top_causal_score * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ delay: index * 0.04 }}
      className={`rounded-xl border transition-colors ${
        signal.status === "promoted"
          ? "border-green-500/30 bg-green-500/5"
          : signal.status === "dismissed"
          ? "border-gray-700/30 bg-gray-800/20 opacity-50"
          : "border-violet-500/20 bg-violet-500/5 hover:border-violet-500/40"
      }`}
    >
      {/* Card header — always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-start gap-3 p-3 text-left"
      >
        <div className="flex-shrink-0 mt-0.5">
          {signal.burst_score >= 0.7
            ? <Zap size={14} className="text-rose-400" />
            : <Radar size={14} className="text-violet-400" />
          }
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-white text-sm font-medium capitalize">{signal.raw_topic}</span>
            <span className={`text-xs font-medium ${burstColor}`}>{burstLabel}</span>
          </div>

          {/* Causal chain preview */}
          <CausalChainBadge hops={signal.causal_chain_plain.split(" → ")} />

          <div className="flex items-center gap-3 mt-1.5 text-xs">
            <span className={`font-medium ${hopColor}`}>{hopLabel} linkage</span>
            <span className="text-gray-600">·</span>
            <span className="text-gray-500">{causalPct}% causal confidence</span>
            <span className="text-gray-600">·</span>
            <span className="text-gray-500">{SOURCE_LABELS[signal.source] ?? signal.source}</span>
          </div>
        </div>

        {isExpanded
          ? <ChevronDown size={14} className="text-gray-500 flex-shrink-0 mt-1" />
          : <ChevronRight size={14} className="text-gray-500 flex-shrink-0 mt-1" />
        }
      </button>

      {/* Expanded detail */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 flex flex-col gap-3">
              {/* Analyst note */}
              <p className="text-gray-400 text-xs leading-relaxed border-l-2 border-violet-500/40 pl-2">
                {signal.analyst_note}
              </p>

              {/* All causal paths */}
              {signal.causal_paths.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-2">Supply chain linkages found</p>
                  <div className="flex flex-col gap-2">
                    {signal.causal_paths.slice(0, 3).map((path, i) => (
                      <CausalPathRow key={i} path={path} />
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              {signal.status === "unreviewed" && (
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => onPromote?.(signal)}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-green-500/10 text-green-400 border border-green-500/20 hover:bg-green-500/20 transition-colors"
                  >
                    <CheckCircle size={12} />
                    Promote to main feed
                  </button>
                  <button
                    onClick={() => onDismiss?.(signal)}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-gray-500/10 text-gray-400 border border-gray-500/20 hover:bg-gray-500/20 transition-colors"
                  >
                    <XCircle size={12} />
                    Dismiss
                  </button>
                </div>
              )}
              {signal.status === "promoted" && (
                <div className="flex items-center gap-1.5 text-xs text-green-400">
                  <CheckCircle size={12} /> Promoted to main feed
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function CausalChainBadge({ hops }: { hops: string[] }) {
  const visible = hops.slice(0, 4);
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {visible.map((hop, i) => (
        <span key={i} className="flex items-center gap-1">
          <span className={`text-xs rounded px-1.5 py-0.5 ${
            i === 0 ? "bg-violet-500/15 text-violet-300" :
            i === visible.length - 1 ? "bg-blue-500/15 text-blue-300" :
            "bg-gray-700/50 text-gray-400"
          }`}>
            {hop.length > 20 ? hop.slice(0, 19) + "…" : hop}
          </span>
          {i < visible.length - 1 && <ArrowRight size={10} className="text-gray-600 flex-shrink-0" />}
        </span>
      ))}
      {hops.length > 4 && <span className="text-gray-600 text-xs">+{hops.length - 4}</span>}
    </div>
  );
}

function CausalPathRow({ path }: { path: import("../../types").CausalPath }) {
  const pct = Math.round(path.causal_score * 100);
  const hopCount = path.hops.length - 1;
  const color = hopCount === 1 ? "text-green-400" : hopCount === 2 ? "text-amber-400" : "text-orange-400";

  return (
    <div className="rounded-lg bg-white/[0.02] border border-white/[0.05] p-2.5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-medium text-gray-300">{path.market_entity}</span>
        <div className="flex items-center gap-1.5">
          <span className={`text-xs ${color}`}>{hopCount} hop{hopCount > 1 ? "s" : ""}</span>
          <span className="text-gray-600">·</span>
          <span className="text-xs text-gray-500">{pct}%</span>
        </div>
      </div>
      <div className="flex items-center gap-1 flex-wrap">
        {path.hops.map((hop, i) => (
          <span key={i} className="flex items-center gap-1">
            <span className="text-xs text-gray-400">{hop}</span>
            {i < path.hops.length - 1 && (
              <span className="text-gray-600 text-xs">
                {path.relationship_chain[i] ? `(${path.relationship_chain[i]})` : "→"}
              </span>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}
