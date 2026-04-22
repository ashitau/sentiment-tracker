import { useEffect, useRef, useMemo } from "react";
import * as d3 from "d3";
import type { KeywordNode } from "../../types";

interface Props {
  keywords: KeywordNode[];
  onNodeClick: (node: KeywordNode) => void;
  selectedWord: string | null;
}

interface SimNode extends d3.SimulationNodeDatum {
  word: string;
  weight: number;
  mention_count: number;
  sector: string;
  sentiment: string;
  direction: -1 | 0 | 1;
  signal_strength: "Strong" | "Moderate" | "Emerging";
  r: number;
}

const SECTOR_COLORS: Record<string, string> = {
  "Banking & Finance":     "#60a5fa",
  "Information Technology":"#a78bfa",
  "Macro / Policy":        "#fb923c",
  "Automobile":            "#34d399",
  "Energy":                "#fbbf24",
  "Pharmaceuticals":       "#f472b6",
  "FMCG":                  "#4ade80",
  "Metals & Mining":       "#94a3b8",
  "Real Estate":           "#f87171",
  "General Market":        "#9ca3af",
};

function sentimentRing(direction: -1 | 0 | 1): string {
  if (direction === 1) return "#22c55e";
  if (direction === -1) return "#ef4444";
  return "#6b7280";
}

export default function ConstellationMap({ keywords, onNodeClick, selectedWord }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const nodes: SimNode[] = useMemo(() =>
    keywords.map(k => ({
      ...k,
      r: Math.max(18, Math.min(60, 18 + k.weight * 55)),
    })),
  [keywords]);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || nodes.length === 0) return;

    const { width, height } = containerRef.current.getBoundingClientRect();
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    svg.attr("width", width).attr("height", height);

    // Starfield background dots
    const starCount = 120;
    const stars = Array.from({ length: starCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      r: Math.random() * 1.2 + 0.3,
      opacity: Math.random() * 0.5 + 0.1,
    }));
    svg.append("g").selectAll("circle.star")
      .data(stars).enter().append("circle")
      .attr("cx", d => d.x).attr("cy", d => d.y).attr("r", d => d.r)
      .attr("fill", "white").attr("opacity", d => d.opacity);

    const g = svg.append("g");

    // Zoom
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.4, 3])
        .on("zoom", e => g.attr("transform", e.transform))
    );

    // Force simulation
    const sim = d3.forceSimulation<SimNode>(nodes)
      .force("charge", d3.forceManyBody().strength(d => -d.r * 12))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide<SimNode>().radius(d => d.r + 8).iterations(3))
      .force("x", d3.forceX(width / 2).strength(0.05))
      .force("y", d3.forceY(height / 2).strength(0.05));

    // Edges — connect nodes with high co-occurrence (same sector)
    const links: { source: SimNode; target: SimNode; strength: number }[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (nodes[i].sector === nodes[j].sector && nodes[i].signal_strength !== "Emerging") {
          links.push({ source: nodes[i], target: nodes[j], strength: 0.4 });
        }
      }
    }

    const linkSel = g.append("g").selectAll("line")
      .data(links).enter().append("line")
      .attr("stroke", d => SECTOR_COLORS[d.source.sector] || "#374151")
      .attr("stroke-opacity", 0.2)
      .attr("stroke-width", 1);

    // Glow filter
    const defs = svg.append("defs");
    ["green", "red", "blue"].forEach(color => {
      const filter = defs.append("filter").attr("id", `glow-${color}`);
      filter.append("feGaussianBlur").attr("stdDeviation", "4").attr("result", "blur");
      const merge = filter.append("feMerge");
      merge.append("feMergeNode").attr("in", "blur");
      merge.append("feMergeNode").attr("in", "SourceGraphic");
    });

    // Node groups
    const nodeG = g.append("g").selectAll<SVGGElement, SimNode>("g.node")
      .data(nodes).enter().append("g")
      .attr("class", "node")
      .style("cursor", "pointer")
      .on("click", (_, d) => onNodeClick(d));

    // Outer ring (sentiment colour)
    nodeG.append("circle")
      .attr("r", d => d.r + 4)
      .attr("fill", "none")
      .attr("stroke", d => sentimentRing(d.direction))
      .attr("stroke-width", d => d.signal_strength === "Strong" ? 2.5 : 1.2)
      .attr("opacity", d => d.signal_strength === "Emerging" ? 0.3 : 0.7);

    // Main node circle
    nodeG.append("circle")
      .attr("r", d => d.r)
      .attr("fill", d => SECTOR_COLORS[d.sector] || "#374151")
      .attr("fill-opacity", d => d.weight * 0.5 + 0.15)
      .attr("stroke", d => SECTOR_COLORS[d.sector] || "#374151")
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.8)
      .attr("filter", d =>
        d.signal_strength === "Strong"
          ? d.direction === 1 ? "url(#glow-green)" : d.direction === -1 ? "url(#glow-red)" : "url(#glow-blue)"
          : null
      );

    // Label
    nodeG.append("text")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .attr("fill", "white")
      .attr("font-size", d => Math.max(9, Math.min(14, d.r * 0.38)))
      .attr("font-weight", d => d.signal_strength === "Strong" ? "600" : "400")
      .attr("pointer-events", "none")
      .text(d => d.word.length > 14 ? d.word.slice(0, 13) + "…" : d.word);

    // Mention count label
    nodeG.append("text")
      .attr("text-anchor", "middle")
      .attr("y", d => d.r * 0.45)
      .attr("fill", "rgba(255,255,255,0.55)")
      .attr("font-size", 8)
      .attr("pointer-events", "none")
      .text(d => `${d.mention_count}`);

    // Pulse animation on Strong signals
    nodeG.filter(d => d.signal_strength === "Strong")
      .append("circle")
      .attr("r", d => d.r + 4)
      .attr("fill", "none")
      .attr("stroke", d => sentimentRing(d.direction))
      .attr("stroke-width", 1)
      .attr("opacity", 0.6)
      .each(function () { pulsate(d3.select(this)); });

    function pulsate(circle: d3.Selection<SVGCircleElement, SimNode, null, undefined>) {
      circle.transition()
        .duration(1800)
        .attr("r", (d: SimNode) => d.r + 14)
        .attr("opacity", 0)
        .on("end", () => {
          circle.attr("r", (d: SimNode) => d.r + 4).attr("opacity", 0.6);
          pulsate(circle);
        });
    }

    sim.on("tick", () => {
      linkSel
        .attr("x1", d => (d.source as SimNode).x!)
        .attr("y1", d => (d.source as SimNode).y!)
        .attr("x2", d => (d.target as SimNode).x!)
        .attr("y2", d => (d.target as SimNode).y!);
      nodeG.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Drag
    nodeG.call(
      d3.drag<SVGGElement, SimNode>()
        .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
    );

    return () => { sim.stop(); };
  }, [nodes, onNodeClick]);

  // Highlight selected
  useEffect(() => {
    if (!svgRef.current) return;
    d3.select(svgRef.current).selectAll<SVGGElement, SimNode>("g.node")
      .select("circle:nth-child(2)")
      .attr("fill-opacity", d =>
        selectedWord === null || d.word === selectedWord
          ? d.weight * 0.5 + 0.15
          : 0.04
      )
      .attr("stroke-opacity", d =>
        selectedWord === null || d.word === selectedWord ? 0.8 : 0.15
      );
  }, [selectedWord]);

  return (
    <div ref={containerRef} className="relative w-full h-full constellation-canvas rounded-xl overflow-hidden">
      <svg ref={svgRef} className="w-full h-full" />

      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex flex-col gap-2 bg-brand-panel/80 backdrop-blur rounded-lg p-3 border border-brand-border text-xs">
        <div className="text-gray-400 font-medium mb-1">Sentiment ring</div>
        {[
          { color: "#22c55e", label: "Bullish" },
          { color: "#ef4444", label: "Bearish" },
          { color: "#6b7280", label: "Mixed / Neutral" },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full border-2" style={{ borderColor: color }} />
            <span className="text-gray-300">{label}</span>
          </div>
        ))}
        <div className="text-gray-400 font-medium mt-2 mb-1">Node size = signal weight</div>
        <div className="text-gray-500">Drag to explore · Scroll to zoom</div>
      </div>
    </div>
  );
}
