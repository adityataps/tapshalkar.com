"use client";

import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";
import { useCallback, useRef, useState, useEffect, useMemo } from "react";

export interface GraphNode {
  id: string;
  type: "skill" | "project" | "experience" | "education" | "interest" | "movie" | "show" | "health";
  label: string;
  description?: string;
  metadata?: Record<string, unknown>;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface Props {
  data: GraphData;
  activeNodeIds?: string[];
  onNodeClick?: (node: GraphNode) => void;
  graphRef?: React.MutableRefObject<ForceGraphMethods | undefined>;
}

const NODE_COLORS: Record<GraphNode["type"], string> = {
  skill:      "#3b82f6",
  project:    "#34d399",
  experience: "#a78bfa",
  education:  "#fbbf24",
  interest:   "#f472b6",
  movie:      "#fb923c",
  show:       "#f87171",
  health:     "#4ade80",
};

export default function ForceGraph({ data, activeNodeIds = [], onNodeClick, graphRef }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const settled = useRef(false);
  const [cooldownTicks, setCooldownTicks] = useState<number | undefined>(undefined);

  // Internal ref used when no graphRef is passed in from the parent
  const internalRef = useRef<ForceGraphMethods | undefined>(undefined);
  const resolvedRef = graphRef ?? internalRef;

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const nodeColor = useCallback(
    (node: GraphNode) =>
      activeNodeIds.includes(node.id) ? "#ef4444" : NODE_COLORS[node.type] ?? "#888",
    [activeNodeIds]
  );

  const handleEngineStop = useCallback(() => {
    if (!settled.current) {
      settled.current = true;
      setCooldownTicks(0);
      resolvedRef.current?.zoomToFit(400);
    }
  }, [resolvedRef]);

  const graphData = useMemo(() => ({
    nodes: data.nodes.map((n) => ({ ...n })),
    links: data.edges.map((e) => ({ source: e.source, target: e.target, type: e.type, weight: e.weight })),
  }), [data]);

  const nodeLabel = useCallback((node: GraphNode) => {
    const color = NODE_COLORS[node.type] ?? "#888";
    const typeLabel = node.type.charAt(0).toUpperCase() + node.type.slice(1);
    return `<span style="color:${color};font-weight:600">${typeLabel}</span><br/>${node.label}`;
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full">
      {dimensions.width > 0 && (
        <ForceGraph2D
          ref={resolvedRef as React.MutableRefObject<ForceGraphMethods>}
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="#0d0d0d"
          nodeLabel={nodeLabel as (node: object) => string}
          nodeColor={nodeColor as (node: object) => string}
          nodeRelSize={5}
          linkColor={() => "#1e1e1e"}
          linkWidth={(link: object) => ((link as GraphEdge).weight ?? 1) * 1.5}
          onNodeClick={onNodeClick as ((node: object) => void) | undefined}
          cooldownTicks={cooldownTicks}
          onEngineStop={handleEngineStop}
        />
      )}
    </div>
  );
}
