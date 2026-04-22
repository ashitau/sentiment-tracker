import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { SectorHeatmapEntry } from "../../types";

interface Props {
  heatmap: Record<string, SectorHeatmapEntry>;
  onSectorClick: (sector: string) => void;
  activeSector: string | null;
}

const SECTOR_ICONS: Record<string, string> = {
  "Banking & Finance":     "🏦",
  "Information Technology":"💻",
  "Macro / Policy":        "🏛",
  "Automobile":            "🚗",
  "Energy":                "#⚡",
  "Pharmaceuticals":       "💊",
  "FMCG":                  "🛒",
  "Metals & Mining":       "⛏",
  "Real Estate":           "🏢",
  "General Market":        "📈",
};

export default function SectorHeatmap({ heatmap, onSectorClick, activeSector }: Props) {
  const entries = Object.entries(heatmap).sort((a, b) => b[1].score - a[1].score);

  return (
    <div className="rounded-xl border border-brand-border bg-brand-panel p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-200">Sector Sentiment</h3>
        <span className="text-xs text-gray-500">Click to filter constellation</span>
      </div>
      <div className="flex flex-col gap-2 flex-1 overflow-y-auto">
        {entries.map(([sector, data], i) => (
          <SectorRow
            key={sector}
            sector={sector}
            data={data}
            index={i}
            active={activeSector === null || activeSector === sector}
            onClick={() => onSectorClick(sector)}
          />
        ))}
      </div>
    </div>
  );
}

function SectorRow({
  sector, data, index, active, onClick,
}: {
  sector: string;
  data: SectorHeatmapEntry;
  index: number;
  active: boolean;
  onClick: () => void;
}) {
  const DirectionIcon =
    data.direction > 0 ? TrendingUp :
    data.direction < 0 ? TrendingDown : Minus;

  const dirColor =
    data.direction > 0 ? "text-green-400" :
    data.direction < 0 ? "text-red-400" : "text-gray-400";

  const barColor =
    data.direction > 0 ? "bg-green-500" :
    data.direction < 0 ? "bg-red-500" : "bg-gray-500";

  return (
    <motion.div
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: active ? 1 : 0.3, x: 0 }}
      transition={{ delay: index * 0.04 }}
      onClick={onClick}
      className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.04] cursor-pointer border border-transparent hover:border-brand-border transition-all"
    >
      <span className="text-base w-6 flex-shrink-0 text-center">
        {SECTOR_ICONS[sector]?.replace("#", "") ?? "📊"}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-300 truncate">{sector}</span>
          <div className={`flex items-center gap-1 ${dirColor}`}>
            <DirectionIcon size={12} />
            <span className="text-xs">{data.plain_label}</span>
          </div>
        </div>
        {/* Score bar */}
        <div className="w-full bg-gray-800 rounded-full h-1.5">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${data.score * 100}%` }}
            transition={{ duration: 0.8, delay: index * 0.06 }}
            className={`h-1.5 rounded-full ${barColor}`}
          />
        </div>
      </div>
      <span className="text-xs text-gray-500 flex-shrink-0 w-14 text-right">
        {data.mention_count.toLocaleString()} mentions
      </span>
    </motion.div>
  );
}
