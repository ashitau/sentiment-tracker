import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RefreshCw, LayoutGrid, Star, Clock, LogOut } from "lucide-react";
import ConstellationMap from "./components/ConstellationMap/ConstellationMap";
import StakeholderDashboard from "./components/StakeholderDashboard/StakeholderDashboard";
import SectorHeatmap from "./components/SectorHeatmap/SectorHeatmap";
import NarrativeTimeline from "./components/NarrativeTimeline/NarrativeTimeline";
import ValidationPanel from "./components/ValidationMetrics/ValidationMetrics";
import SignalDetailPanel from "./components/common/SignalDetailPanel";
import WeakSignalPanel from "./components/WeakSignals/WeakSignalPanel";
import LoginPage from "./components/Auth/LoginPage";
import { useAuth } from "./hooks/useAuth";
import { MOCK_DASHBOARD } from "./utils/mock";
import type { EntitySignal, KeywordNode, WeakSignal } from "./types";
import { formatDistanceToNow } from "date-fns";

type Tab = "constellation" | "stakeholder" | "signals";

const WINDOW_OPTIONS = [1, 3, 6, 12, 24];

export default function App() {
  const { status, email, requestLink, verifyToken, logout } = useAuth();

  // Read magic-link token from URL on first load
  const urlToken = new URLSearchParams(window.location.search).get("token");

  // Show login page until authenticated
  if (status === "checking") {
    return (
      <div className="min-h-screen bg-brand-bg flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    return (
      <LoginPage
        onRequestLink={requestLink}
        onVerifyToken={verifyToken}
        verifyTokenFromUrl={urlToken}
      />
    );
  }

  return <Dashboard email={email!} onLogout={logout} />;
}

function Dashboard({ email, onLogout }: { email: string; onLogout: () => void }) {
  const [activeTab, setActiveTab] = useState<Tab>("constellation");
  const [windowHours, setWindowHours] = useState(6);
  const [selectedWord, setSelectedWord] = useState<string | null>(null);
  const [selectedSignal, setSelectedSignal] = useState<EntitySignal | null>(null);
  const [activeSector, setActiveSector] = useState<string | null>(null);
  const [weakSignals, setWeakSignals] = useState(MOCK_DASHBOARD.weak_signals);

  // Use mock data — swap for useDashboard(windowHours) when backend is live
  const data = MOCK_DASHBOARD;
  const isLoading = false;

  const filteredKeywords = useMemo(() => {
    if (!activeSector) return data.trending_keywords;
    return data.trending_keywords.filter(k => k.sector === activeSector || k.sector === "General Market");
  }, [data.trending_keywords, activeSector]);

  function handleNodeClick(node: KeywordNode) {
    setSelectedWord(node.word);
    const match = data.top_signals.find(s => s.canonical_name === node.word);
    setSelectedSignal(match ?? null);
  }

  function handlePromote(signal: WeakSignal) {
    setWeakSignals(prev => prev.map(s => s.raw_topic === signal.raw_topic ? { ...s, status: "promoted" as const } : s));
  }

  function handleDismiss(signal: WeakSignal) {
    setWeakSignals(prev => prev.map(s => s.raw_topic === signal.raw_topic ? { ...s, status: "dismissed" as const } : s));
  }

  function handleSectorClick(sector: string) {
    setActiveSector(prev => prev === sector ? null : sector);
    setSelectedWord(null);
    setSelectedSignal(null);
  }

  const generatedAt = new Date(data.generated_at);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-brand-bg text-gray-200 font-sans">
      {/* Top bar */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-brand-border flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <span className="text-sm font-bold text-white tracking-tight">ET Now · Sentiment Tracker</span>
            <span className="text-xs text-gray-500">
              Updated {formatDistanceToNow(generatedAt, { addSuffix: true })} · {data.validation.window_label}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Window selector */}
          <div className="flex items-center gap-1 bg-brand-panel rounded-lg p-1 border border-brand-border">
            <Clock size={12} className="text-gray-500 ml-1" />
            {WINDOW_OPTIONS.map(h => (
              <button
                key={h}
                onClick={() => setWindowHours(h)}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  windowHours === h
                    ? "bg-brand-accent text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {h}h
              </button>
            ))}
          </div>

          {/* Tab toggle */}
          <div className="flex items-center gap-1 bg-brand-panel rounded-lg p-1 border border-brand-border">
            <TabBtn active={activeTab === "constellation"} onClick={() => setActiveTab("constellation")} icon={<Star size={13} />} label="Constellation" />
            <TabBtn active={activeTab === "stakeholder"}  onClick={() => setActiveTab("stakeholder")}  icon={<LayoutGrid size={13} />} label="Briefing" />
            <TabBtn active={activeTab === "signals"}      onClick={() => setActiveTab("signals")}      icon={<span className="text-violet-400 font-bold text-xs">⬡</span>} label={`Signals to Watch${weakSignals.filter(s => s.status === "unreviewed").length > 0 ? ` · ${weakSignals.filter(s => s.status === "unreviewed").length}` : ""}`} />
          </div>

          <button
            onClick={() => {}}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg border border-brand-border hover:border-gray-500"
          >
            <RefreshCw size={12} className={isLoading ? "animate-spin" : ""} />
            Refresh
          </button>

          {/* User + logout */}
          <div className="flex items-center gap-2 pl-2 border-l border-brand-border">
            <span className="text-xs text-gray-500 hidden sm:block">{email}</span>
            <button
              onClick={onLogout}
              title="Sign out"
              className="text-gray-500 hover:text-white transition-colors p-1 rounded"
            >
              <LogOut size={13} />
            </button>
          </div>
        </div>
      </header>

      {/* Validation bar */}
      <div className="flex-shrink-0">
        <ValidationPanel validation={data.validation} />
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          {activeTab === "constellation" ? (
            <motion.div
              key="constellation"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="h-full flex gap-0"
            >
              {/* Left: sector heatmap */}
              <div className="w-56 flex-shrink-0 border-r border-brand-border overflow-hidden">
                <SectorHeatmap
                  heatmap={data.sector_heatmap}
                  onSectorClick={handleSectorClick}
                  activeSector={activeSector}
                />
              </div>

              {/* Centre: constellation map */}
              <div className="flex-1 relative overflow-hidden">
                <ConstellationMap
                  keywords={filteredKeywords}
                  onNodeClick={handleNodeClick}
                  selectedWord={selectedWord}
                />
                {/* Signal detail panel overlays right side of map */}
                <SignalDetailPanel
                  signal={selectedSignal}
                  onClose={() => { setSelectedSignal(null); setSelectedWord(null); }}
                />
              </div>

              {/* Right: narrative timeline */}
              <div className="w-72 flex-shrink-0 border-l border-brand-border overflow-hidden">
                <NarrativeTimeline clusters={data.topic_clusters} />
              </div>
            </motion.div>
          ) : activeTab === "stakeholder" ? (
            <motion.div
              key="stakeholder"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="h-full overflow-y-auto p-5"
            >
              <StakeholderDashboard
                validation={data.validation}
                topSignals={data.top_signals}
              />
            </motion.div>
          ) : (
            <motion.div
              key="signals"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="h-full overflow-hidden"
            >
              <WeakSignalPanel
                signals={weakSignals}
                onPromote={handlePromote}
                onDismiss={handleDismiss}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function TabBtn({
  active, onClick, icon, label,
}: {
  active: boolean; onClick: () => void; icon: React.ReactNode; label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1 text-xs rounded-md transition-colors ${
        active ? "bg-brand-accent text-white" : "text-gray-400 hover:text-white"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
