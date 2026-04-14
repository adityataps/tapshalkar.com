"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { ForceGraphMethods } from "react-force-graph-2d";
import type { GraphData, GraphNode } from "./types";

const ForceGraph = dynamic(() => import("./ForceGraph"), { ssr: false });

const EMPTY_GRAPH: GraphData = { nodes: [], edges: [] };

interface Props {
  activeNodeIds?: string[];
  selectedNodeIds?: string[];
  onNodeSelect?: (node: GraphNode) => void;
  rightPanel?: React.ReactNode;
}

export default function GraphPanel({ activeNodeIds = [], selectedNodeIds = [], onNodeSelect, rightPanel }: Props) {
  const [data, setData] = useState<GraphData>(EMPTY_GRAPH);
  const [expanded, setExpanded] = useState(false);
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/graph`)
      .then((r) => { if (!r.ok) return null; return r.json(); })
      .then((d) => d && setData(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleReset = () => graphRef.current?.zoomToFit(400);

  const controls = (
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
  );

  const graph = (
    <ForceGraph
      data={data}
      activeNodeIds={activeNodeIds}
      selectedNodeIds={selectedNodeIds}
      onNodeClick={onNodeSelect}
      graphRef={graphRef}
    />
  );

  if (expanded) {
    return (
      <div className="fixed inset-0 z-50 bg-[#0d0d0d] flex transition-all duration-300">
        <div className="flex-1 relative overflow-hidden">
          {controls}
          {graph}
        </div>
        {rightPanel && (
          <div className="w-[360px] border-l border-[#1e1e1e] flex-shrink-0 flex flex-col">
            <div className="flex justify-end px-4 pt-3 pb-2 border-b border-[#1e1e1e]">
              <button
                onClick={() => setExpanded(false)}
                className="text-[#444444] hover:text-[#f5f5f0] text-xs transition-colors"
                title="Close"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 min-h-0 p-4">
              {rightPanel}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-[#0d0d0d] rounded-lg overflow-hidden border border-[#1e1e1e]">
      {controls}
      {graph}
    </div>
  );
}
