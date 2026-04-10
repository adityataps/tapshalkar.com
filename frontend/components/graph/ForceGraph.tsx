"use client";

import { useEffect, useRef } from "react";

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
  const graphRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let destroyed = false;

    import("react-force-graph-2d").then(({ default: ForceGraph2D }) => {
      if (destroyed || !containerRef.current) return;

      const { width, height } = containerRef.current.getBoundingClientRect();

      const fg = new (ForceGraph2D as any)()
        .graphData({
          nodes: data.nodes.map((n) => ({ ...n })),
          links: data.edges.map((e) => ({ source: e.source, target: e.target, type: e.type })),
        })
        .width(width)
        .height(height)
        .backgroundColor("#0d0d0d")
        .nodeLabel("label")
        .nodeColor((node: GraphNode) =>
          activeNodeIds.includes(node.id) ? "#ef4444" : NODE_COLORS[node.type] ?? "#888"
        )
        .nodeRelSize(5)
        .linkColor(() => "#1e1e1e")
        .linkWidth((link: any) => (link.weight ?? 1) * 1.5)
        .onNodeClick((node: GraphNode) => onNodeClick?.(node))(containerRef.current);

      graphRef.current = fg;
    });

    return () => {
      destroyed = true;
      graphRef.current?._destructor?.();
    };
  }, [data, activeNodeIds, onNodeClick]);

  return <div ref={containerRef} className="w-full h-full" />;
}
