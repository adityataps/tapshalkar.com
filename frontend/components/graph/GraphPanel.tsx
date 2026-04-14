"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { ForceGraphMethods } from "react-force-graph-2d";
import type { GraphData, GraphNode } from "./types";

const ForceGraph = dynamic(() => import("./ForceGraph"), { ssr: false });

const EMPTY_GRAPH: GraphData = { nodes: [], edges: [] };

interface Props {
  activeNodeIds?: string[];
  agentZoomTrigger?: number;
  selectedNodeIds?: string[];
  onNodeSelect?: (node: GraphNode) => void;
  onDeselectAll?: () => void;
  rightPanel?: React.ReactNode;
}

export default function GraphPanel({ activeNodeIds = [], agentZoomTrigger, selectedNodeIds = [], onNodeSelect, onDeselectAll, rightPanel }: Props) {
  const [data, setData] = useState<GraphData>(EMPTY_GRAPH);
  const [expanded, setExpanded] = useState(false);
  const [chatOpen, setChatOpen] = useState(true);
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

  useEffect(() => {
    if (!agentZoomTrigger || activeNodeIds.length === 0) return;
    const t = setTimeout(() => {
      const padding = activeNodeIds.length === 1 ? 200 : 150;
      graphRef.current?.zoomToFit(600, padding, (node) => activeNodeIds.includes((node as GraphNode).id));
    }, 150);
    return () => clearTimeout(t);
  }, [agentZoomTrigger]); // eslint-disable-line react-hooks/exhaustive-deps

  const nodeEdgeCount = data.nodes.length > 0 && (
    <div className="absolute bottom-4 right-4 z-10 font-mono text-[#555555] text-[9px] tracking-[0.12em] select-none">
      {data.nodes.length} nodes · {data.edges.length} edges
    </div>
  );

  const controls = (
    <div className="absolute bottom-4 left-4 z-10 flex gap-2 items-center">
      <button
        onClick={handleReset}
        className="text-[#777777] hover:text-[#f5f5f0] text-xs px-2 py-1 border border-[#444444] hover:border-[#f5f5f0] transition-colors"
        title="Reset view"
      >
        ↺
      </button>
      <button
        onClick={() => setExpanded((e) => !e)}
        className="text-[#777777] hover:text-[#f5f5f0] text-xs px-2 py-1 border border-[#444444] hover:border-[#f5f5f0] transition-colors"
        title={expanded ? "Collapse" : "Expand"}
      >
        {expanded ? "⊠" : "⤢"}
      </button>
      {selectedNodeIds.length > 0 && onDeselectAll && (
        <button
          onClick={onDeselectAll}
          className="text-[#22d3ee] hover:text-[#f5f5f0] border border-[#22d3ee] hover:border-[#f5f5f0] font-mono text-[9px] px-2 py-1 tracking-[0.1em] transition-colors"
        >
          deselect all ({selectedNodeIds.length})
        </button>
      )}
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
          {nodeEdgeCount}
          {graph}
          {rightPanel && !chatOpen && (
            <button
              onClick={() => setChatOpen(true)}
              className="absolute top-1/2 right-0 -translate-y-1/2 z-10 px-1.5 py-3 border border-r-0 border-[#1e1e1e] bg-[#0d0d0d] text-[#777777] hover:text-[#f5f5f0] hover:border-[#444444] transition-colors"
              title="Open chat"
            >
              <span className="font-mono text-xs">‹</span>
            </button>
          )}
        </div>
        {rightPanel && chatOpen && (
          <div className="w-[360px] border-l border-[#1e1e1e] flex-shrink-0 flex flex-col">
            <div className="flex justify-between px-4 pt-3 pb-2 border-b border-[#1e1e1e]">
              <button
                onClick={() => setChatOpen(false)}
                className="text-[#777777] hover:text-[#f5f5f0] text-xs transition-colors"
                title="Collapse chat"
              >
                ›
              </button>
              <button
                onClick={() => setExpanded(false)}
                className="text-[#777777] hover:text-[#f5f5f0] text-xs transition-colors"
                title="Exit fullscreen"
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
      {nodeEdgeCount}
      {graph}
    </div>
  );
}
