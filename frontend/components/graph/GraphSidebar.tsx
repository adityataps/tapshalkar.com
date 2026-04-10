import type { GraphNode } from "./ForceGraph";

interface Props {
  node: GraphNode | null;
  onClose: () => void;
}

export default function GraphSidebar({ node, onClose }: Props) {
  if (!node) return null;

  return (
    <div className="absolute right-0 top-0 bottom-0 w-64 bg-[#111111] border-l border-[#1e1e1e] p-5 z-10">
      <button
        onClick={onClose}
        className="absolute top-3 right-3 text-[#444444] hover:text-[#f5f5f0] text-xs font-mono"
      >
        [close]
      </button>
      <p className="font-mono text-[#ef4444] text-xs tracking-widest uppercase mb-2">{node.type}</p>
      <h3 className="font-serif text-[#f5f5f0] text-lg font-bold mb-2">{node.label}</h3>
      {node.description && (
        <p className="text-[#444444] text-xs leading-relaxed">{node.description}</p>
      )}
    </div>
  );
}
