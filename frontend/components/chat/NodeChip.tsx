import type { GraphNode } from "@/components/graph/ForceGraph";
import { NODE_COLORS } from "@/components/graph/ForceGraph";

interface Props {
  node: GraphNode;
  onRemove: (id: string) => void;
}

export default function NodeChip({ node, onRemove }: Props) {
  const dotColor = NODE_COLORS[node.type] ?? "#888";

  return (
    <div className="relative group inline-flex">
      <div className="bg-[#0d0d0d] border border-[#22d3ee] text-[#22d3ee] font-mono text-[9px] px-2 py-1 flex items-center gap-1.5 cursor-default">
        <span
          className="w-1.5 h-1.5 rounded-full flex-shrink-0"
          style={{ background: dotColor }}
        />
        <span>{node.label}</span>
        <button
          onClick={() => onRemove(node.id)}
          className="text-[#444444] hover:text-[#f5f5f0] leading-none ml-0.5"
          aria-label={`Remove ${node.label}`}
        >
          ×
        </button>
      </div>
      {node.description && (
        <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block z-20 w-44 bg-[#111111] border border-[#333333] text-[#999999] font-mono text-[8px] leading-relaxed px-2 py-1.5 pointer-events-none">
          {node.description}
        </div>
      )}
    </div>
  );
}
