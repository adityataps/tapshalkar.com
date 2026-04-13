"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { ForceGraphMethods } from "react-force-graph-2d";
import type { GraphData, GraphNode } from "./ForceGraph";
import GraphSidebar from "./GraphSidebar";

const ForceGraph = dynamic(() => import("./ForceGraph"), { ssr: false });

const EMPTY_GRAPH: GraphData = { nodes: [], edges: [] };

interface Props {
  activeNodeIds?: string[];
}

// Graph data is fetched client-side on mount — never at build time.
// This satisfies the static export constraint (no server-side API calls during next build).
export default function GraphPanel({ activeNodeIds = [] }: Props) {
  const [data, setData] = useState<GraphData>(EMPTY_GRAPH);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [expanded, setExpanded] = useState(false);
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/graph`)
      .then((r) => { if (!r.ok) return null; return r.json(); })
      .then((d) => d && setData(d))
      .catch(() => {}); // fail silently — graph stays empty
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleReset = () => graphRef.current?.zoomToFit(400);

  const panelClass = expanded
    ? "fixed inset-0 z-50 bg-[#0d0d0d] transition-all duration-300"
    : "relative w-full h-full bg-[#0d0d0d] rounded-lg overflow-hidden border border-[#1e1e1e]";

  return (
    <div className={panelClass}>
      <div className="absolute bottom-4 left-4 z-10 flex gap-2">
        <button
          onClick={handleReset}
          className="text-[#444444] hover:text-[#f5f5f0] text-xs px-2 py-1 border border-[#444444] hover:border-[#f5f5f0] transition-colors"
          title="Reset view"
        >
          ↺
        </button>
        <button
          onClick={() => setExpanded((e) => !e)}
          className="text-[#444444] hover:text-[#f5f5f0] text-xs px-2 py-1 border border-[#444444] hover:border-[#f5f5f0] transition-colors"
          title={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? "⊠" : "⤢"}
        </button>
      </div>

      <ForceGraph
        data={data}
        activeNodeIds={activeNodeIds}
        onNodeClick={setSelected}
        graphRef={graphRef}
      />
      <GraphSidebar node={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
