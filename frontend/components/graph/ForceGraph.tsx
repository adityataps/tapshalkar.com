"use client";

import ForceGraph2D from "react-force-graph-2d";
import { useCallback, useRef, useState, useEffect } from "react";

export interface GraphNode {
  id: string;
  type: "skill" | "project" | "experience" | "education" | "interest";
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
}

const NODE_COLORS: Record<GraphNode["type"], string> = {
  skill:      "#3b82f6",
  project:    "#34d399",
  experience: "#a78bfa",
  education:  "#fbbf24",
  interest:   "#f472b6",
};

export default function ForceGraph({ data, activeNodeIds = [], onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

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
    (node: GraphNode) => activeNodeIds.includes(node.id) ? "#ef4444" : NODE_COLORS[node.type] ?? "#888",
    [activeNodeIds]
  );

  const graphData = {
    nodes: data.nodes.map((n) => ({ ...n })),
    links: data.edges.map((e) => ({ source: e.source, target: e.target, type: e.type, weight: e.weight })),
  };

  return (
    <div ref={containerRef} className="w-full h-full">
      {dimensions.width > 0 && (
        <ForceGraph2D
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="#0d0d0d"
          nodeLabel="label"
          nodeColor={nodeColor as (node: object) => string}
          nodeRelSize={5}
          linkColor={() => "#1e1e1e"}
          linkWidth={(link: object) => ((link as GraphEdge).weight ?? 1) * 1.5}
          onNodeClick={onNodeClick as ((node: object) => void) | undefined}
        />
      )}
    </div>
  );
}
