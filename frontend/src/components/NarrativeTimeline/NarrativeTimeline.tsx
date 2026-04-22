import { motion } from "framer-motion";
import { Zap } from "lucide-react";
import type { TopicCluster } from "../../types";

interface Props {
  clusters: TopicCluster[];
}

export default function NarrativeTimeline({ clusters }: Props) {
  return (
    <div className="rounded-xl border border-brand-border bg-brand-panel p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-200">Narrative Clusters</h3>
        <span className="text-xs text-gray-500">What stories are forming</span>
      </div>
      <div className="flex flex-col gap-3 flex-1 overflow-y-auto">
        {clusters.map((cluster, i) => (
          <NarrativeCard key={cluster.topic_id} cluster={cluster} index={i} />
        ))}
      </div>
    </div>
  );
}

function NarrativeCard({ cluster, index }: { cluster: TopicCluster; index: number }) {
  const isBursting = cluster.trend_velocity > 1.3;
  const isGrowing = cluster.trend_velocity > 0.8;

  const velocityLabel =
    isBursting ? "Accelerating" :
    isGrowing  ? "Growing" : "Stable";
  const velocityColor =
    isBursting ? "text-amber-400" :
    isGrowing  ? "text-blue-400"  : "text-gray-500";

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="p-3 rounded-lg bg-white/[0.02] border border-brand-border hover:border-gray-600 transition-colors"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          {isBursting && <Zap size={13} className="text-amber-400 flex-shrink-0" />}
          <span className="text-white text-sm font-medium leading-tight">{cluster.plain_label}</span>
        </div>
        <span className={`text-xs flex-shrink-0 font-medium ${velocityColor}`}>{velocityLabel}</span>
      </div>

      {/* Keywords */}
      <div className="flex flex-wrap gap-1.5 mb-2">
        {cluster.keywords.slice(0, 5).map(([word, score]) => (
          <span
            key={word}
            className="text-xs px-2 py-0.5 rounded-full bg-white/[0.06] text-gray-300 border border-white/[0.08]"
            style={{ opacity: 0.5 + score * 0.5 }}
          >
            {word}
          </span>
        ))}
      </div>

      {/* Representative excerpt */}
      {cluster.representative_docs[0] && (
        <p className="text-gray-500 text-xs leading-relaxed line-clamp-2 italic">
          "{cluster.representative_docs[0].slice(0, 120)}{cluster.representative_docs[0].length > 120 ? "…" : ""}"
        </p>
      )}

      <div className="flex items-center gap-3 mt-2 text-xs text-gray-600">
        <span>{cluster.document_count} posts</span>
        {cluster.sectors.length > 0 && <span>· {cluster.sectors[0]}</span>}
      </div>
    </motion.div>
  );
}
