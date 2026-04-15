"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { ForceGraphMethods } from "react-force-graph-2d";
import type { GraphData, GraphNode } from "./types";
import { NODE_COLORS } from "./types";

const ForceGraph = dynamic(() => import("./ForceGraph"), { ssr: false });

const EMPTY_GRAPH: GraphData = { nodes: [], edges: [] };

interface Props {
  activeNodeIds?: string[];
  agentZoomTrigger?: number;
  selectedNodeIds?: string[];
  isContextFull?: boolean;
  onNodeSelect?: (node: GraphNode) => void;
  onDeselectAll?: () => void;
  rightPanel?: React.ReactNode;
}

export default function GraphPanel({ activeNodeIds = [], agentZoomTrigger, selectedNodeIds = [], isContextFull = false, onNodeSelect, onDeselectAll, rightPanel }: Props) {
  const [data, setData] = useState<GraphData>(EMPTY_GRAPH);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [chatOpen, setChatOpen] = useState(true);
  const [isTouch, setIsTouch] = useState(false);
  const [peekNode, setPeekNode] = useState<GraphNode | null>(null);
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined);

  useEffect(() => {
    setIsTouch(window.matchMedia("(pointer: coarse)").matches);
  }, []);

  const handleNodeClick = (node: GraphNode) => {
    if (isTouch) {
      setPeekNode(node);
    } else {
      onNodeSelect?.(node);
    }
  };

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/graph`)
      .then((r) => { if (!r.ok) return null; return r.json(); })
      .then((d) => { if (d) setData(d); })
      .catch(() => {})
      .finally(() => setLoading(false));
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
      const padding = activeNodeIds.length === 1 ? 200 : 80;
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

  const loadingOverlay = loading && (
    <div className="absolute inset-0 flex items-center justify-center z-10">
      <span className="font-mono text-[#555555] text-[10px] tracking-[0.2em] uppercase animate-pulse">
        loading graph...
      </span>
    </div>
  );

  const graph = (
    <ForceGraph
      data={data}
      activeNodeIds={activeNodeIds}
      selectedNodeIds={selectedNodeIds}
      peekNodeId={peekNode?.id}
      onNodeClick={handleNodeClick}
      graphRef={graphRef}
    />
  );

  const isSelected = peekNode ? selectedNodeIds.includes(peekNode.id) : false;
  const isActive = peekNode ? activeNodeIds.includes(peekNode.id) : false;
  const peekSubtype = typeof peekNode?.metadata?.subtype === "string" ? peekNode.metadata.subtype : undefined;
  const peekUrl = typeof peekNode?.metadata?.url === "string" ? peekNode.metadata.url : undefined;

  const nodeSheet = peekNode && (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={() => setPeekNode(null)}
      />
      {/* Sheet */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-[#111111] border-t border-[#1e1e1e] px-5 pt-4 pb-8 rounded-t-xl">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="shrink-0 w-2 h-2 rounded-full"
              style={{ backgroundColor: NODE_COLORS[peekNode.type] ?? "#888" }}
            />
            <span
              className="font-mono text-[10px] tracking-[0.15em] uppercase"
              style={{ color: NODE_COLORS[peekNode.type] ?? "#888" }}
            >
              {peekSubtype ?? peekNode.type}
            </span>
            {isActive && (
              <span className="font-mono text-[9px] tracking-[0.1em] text-[#ef4444] border border-[#ef4444] px-1.5 py-0.5">
                agent ref
              </span>
            )}
          </div>
          <button
            onClick={() => setPeekNode(null)}
            className="shrink-0 text-[#555555] hover:text-[#f5f5f0] text-sm transition-colors"
          >
            ✕
          </button>
        </div>

        <p className="text-[#f5f5f0] font-serif text-lg leading-snug mb-2">{peekNode.label}</p>

        {peekNode.description && (
          <p className="text-[#777777] text-xs leading-relaxed mb-4">{peekNode.description}</p>
        )}

        {peekUrl && (
          <a
            href={peekUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[10px] text-[#777777] hover:text-[#ef4444] underline underline-offset-2 block mb-4 transition-colors"
          >
            {peekUrl}
          </a>
        )}

        <button
          onClick={() => { onNodeSelect?.(peekNode); setPeekNode(null); }}
          disabled={!isSelected && isContextFull}
          className={`w-full font-mono text-xs py-2.5 border transition-colors ${
            isSelected
              ? "border-[#22d3ee] text-[#22d3ee] hover:border-[#555555] hover:text-[#777777]"
              : isContextFull
              ? "border-[#333333] text-[#444444] cursor-not-allowed"
              : "border-[#ef4444] text-[#ef4444] hover:border-[#f5f5f0] hover:text-[#f5f5f0]"
          }`}
        >
          {isSelected ? "remove from context" : isContextFull ? "context full (5/5)" : "add to context"}
        </button>
      </div>
    </>
  );

  if (expanded) {
    return (
      <div className="fixed inset-0 z-50 bg-[#0d0d0d] flex transition-all duration-300">
        {nodeSheet}
        <div className="flex-1 relative overflow-hidden">
          {controls}
          {nodeEdgeCount}
          {loadingOverlay}
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
      {loadingOverlay}
      {graph}
      {nodeSheet}
    </div>
  );
}
