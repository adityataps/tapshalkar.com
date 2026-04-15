"use client";

import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";
import { useCallback, useRef, useState, useEffect, useMemo } from "react";
import { GraphNode, GraphEdge, GraphData, NODE_COLORS } from "./types";
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { forceX, forceY, forceCollide } = require("d3-force-3d");

export type { GraphNode, GraphEdge, GraphData };
export { NODE_COLORS };

interface Props {
  data: GraphData;
  activeNodeIds?: string[];
  selectedNodeIds?: string[];
  peekNodeId?: string;
  onNodeClick?: (node: GraphNode) => void;
  graphRef?: React.MutableRefObject<ForceGraphMethods | undefined>;
}

export default function ForceGraph({ data, activeNodeIds = [], selectedNodeIds = [], peekNodeId, onNodeClick, graphRef }: Props) {
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

  // Tune forces: push unconnected nodes apart while keeping connected ones close
  useEffect(() => {
    if (dimensions.width === 0) return;
    const fg = resolvedRef.current;
    if (!fg) return;
    fg.d3Force("x", forceX(0).strength(0.04));
    fg.d3Force("y", forceY(0).strength(0.04));
    fg.d3Force("charge")?.strength(-300).distanceMax(250);
    fg.d3Force("collide", forceCollide(16));
    fg.d3Force("link")?.strength(0.2).distance(10);
  }, [dimensions.width]); // eslint-disable-line react-hooks/exhaustive-deps

  const graphData = useMemo(() => ({
    nodes: data.nodes.map((n) => ({ ...n })),
    links: data.edges.map((e) => ({ source: e.source, target: e.target, type: e.type, weight: e.weight })),
  }), [data.nodes, data.edges]);

  const activeSet = useMemo(() => new Set(activeNodeIds), [activeNodeIds]);
  const selectedSet = useMemo(() => new Set(selectedNodeIds), [selectedNodeIds]);
  const isPeek = useCallback((id: string) => id === peekNodeId, [peekNodeId]);

  const nodeColor = useCallback(
    (node: GraphNode) => NODE_COLORS[node.type] ?? "#888",
    []
  );

  const nodeCanvasObject = useCallback(
    (node: object, ctx: CanvasRenderingContext2D) => {
      const n = node as GraphNode;
      const r = 5;
      const x = n.x ?? 0;
      const y = n.y ?? 0;

      const dimmed = activeSet.size > 0 && !activeSet.has(n.id) && !selectedSet.has(n.id);
      ctx.globalAlpha = dimmed ? 0.2 : 1;

      // Always fill with type color
      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI);
      ctx.fillStyle = NODE_COLORS[n.type] ?? "#888";
      ctx.fill();

      // Dashed ring for peek node (mobile: bottom sheet open, not yet added to context)
      if (isPeek(n.id) && !selectedSet.has(n.id)) {
        ctx.beginPath();
        ctx.arc(x, y, r + 2.5, 0, 2 * Math.PI);
        ctx.setLineDash([2, 2]);
        ctx.strokeStyle = "#f5f5f0";
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Cyan ring for user-selected nodes
      if (selectedSet.has(n.id)) {
        ctx.beginPath();
        ctx.arc(x, y, r + 2.5, 0, 2 * Math.PI);
        ctx.strokeStyle = "#22d3ee";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Red ring for agent-referenced nodes
      if (activeSet.has(n.id)) {
        ctx.beginPath();
        ctx.arc(x, y, r + 2.5, 0, 2 * Math.PI);
        ctx.strokeStyle = "#ef4444";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      ctx.globalAlpha = 1;
    },
    [selectedSet, activeSet, isPeek]
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
          warmupTicks={500}
          d3VelocityDecay={0.7}
          d3AlphaDecay={0.04}
          linkColor={linkColor}
          linkWidth={linkWidth}
          onNodeClick={onNodeClick as ((node: object) => void) | undefined}
        />
      )}
    </div>
  );
}
