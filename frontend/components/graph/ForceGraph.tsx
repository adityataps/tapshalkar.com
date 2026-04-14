"use client";

import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";
import { useCallback, useRef, useState, useEffect, useMemo } from "react";
import { GraphNode, GraphEdge, GraphData, NODE_COLORS } from "./types";

export type { GraphNode, GraphEdge, GraphData };
export { NODE_COLORS };

interface Props {
  data: GraphData;
  activeNodeIds?: string[];
  selectedNodeIds?: string[];
  onNodeClick?: (node: GraphNode) => void;
  graphRef?: React.MutableRefObject<ForceGraphMethods | undefined>;
}

export default function ForceGraph({ data, activeNodeIds = [], selectedNodeIds = [], onNodeClick, graphRef }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

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

  const graphData = useMemo(() => ({
    nodes: data.nodes.map((n) => ({ ...n })),
    links: data.edges.map((e) => ({ source: e.source, target: e.target, type: e.type, weight: e.weight })),
  }), [data.nodes, data.edges]);

  const activeSet = useMemo(() => new Set(activeNodeIds), [activeNodeIds]);
  const selectedSet = useMemo(() => new Set(selectedNodeIds), [selectedNodeIds]);

  const nodeColor = useCallback(
    (node: GraphNode) => activeSet.has(node.id) ? "#ef4444" : (NODE_COLORS[node.type] ?? "#888"),
    [activeSet]
  );

  const nodeCanvasObject = useCallback(
    (node: object, ctx: CanvasRenderingContext2D) => {
      const n = node as GraphNode;
      const r = 5;
      const x = n.x ?? 0;
      const y = n.y ?? 0;

      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI);
      ctx.fillStyle = activeSet.has(n.id) ? "#ef4444" : (NODE_COLORS[n.type] ?? "#888");
      ctx.fill();

      if (selectedSet.has(n.id)) {
        ctx.beginPath();
        ctx.arc(x, y, r + 2.5, 0, 2 * Math.PI);
        ctx.strokeStyle = "#22d3ee";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    },
    [selectedSet, activeSet]
  );

  const linkColor = useCallback(
    (link: object) => {
      const l = link as { source: string | GraphNode; target: string | GraphNode };
      const src = typeof l.source === "string" ? l.source : (l.source as GraphNode).id;
      const tgt = typeof l.target === "string" ? l.target : (l.target as GraphNode).id;
      return activeSet.has(src) && activeSet.has(tgt) ? "#ef4444" : "#1e1e1e";
    },
    [activeSet]
  );

  const linkWidth = useCallback(
    (link: object) => ((link as GraphEdge).weight ?? 1) * 1.5,
    []
  );

  const nodeLabel = useCallback((node: GraphNode) => {
    const color = NODE_COLORS[node.type] ?? "#888";
    const subtype = node.metadata?.subtype as string | undefined;
    const raw = subtype ?? node.type;
    const display = raw.charAt(0).toUpperCase() + raw.slice(1);
    return `<span style="color:${color};font-weight:600">${display}</span><br/>${node.label}`;
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
          nodeCanvasObject={nodeCanvasObject}
          nodeCanvasObjectMode={() => "replace"}
          nodeRelSize={5}
          warmupTicks={150}
          linkColor={linkColor}
          linkWidth={linkWidth}
          onNodeClick={onNodeClick as ((node: object) => void) | undefined}
        />
      )}
    </div>
  );
}
