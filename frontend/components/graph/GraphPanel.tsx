"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
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

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/graph`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {}); // fail silently — graph stays empty
  }, []);

  return (
    <div className="relative w-full h-full bg-[#0d0d0d] rounded-lg overflow-hidden border border-[#1e1e1e]">
      <ForceGraph
        data={data}
        activeNodeIds={activeNodeIds}
        onNodeClick={setSelected}
      />
      <GraphSidebar node={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
