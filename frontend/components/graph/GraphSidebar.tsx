import type { GraphNode } from "./ForceGraph";

interface Props {
  node: GraphNode | null;
  onClose: () => void;
}

export default function GraphSidebar({ node, onClose }: Props) {
  if (!node) return null;

  const url = node.metadata?.url as string | undefined;
  const displayType = (node.metadata?.subtype as string | undefined) ?? node.type;

  return (
    <div className="absolute right-0 top-0 bottom-0 w-64 bg-[#111111] border-l border-[#1e1e1e] p-5 z-10">
      <button
        onClick={onClose}
        className="absolute top-3 right-3 text-[#444444] hover:text-[#f5f5f0] text-xs font-mono"
      >
        [close]
      </button>
      <p className="font-mono text-[#ef4444] text-xs tracking-widest uppercase mb-2">{displayType}</p>
      <h3 className="font-serif text-[#f5f5f0] text-lg font-bold mb-3">{node.label}</h3>
      {node.description && (
        <p className="text-[#444444] text-xs leading-relaxed mb-4">{node.description}</p>
      )}
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-xs border border-[#1e1e1e] text-[#444444] hover:text-[#ef4444] hover:border-[#ef4444] transition-colors px-3 py-1.5 inline-block"
        >
          view →
        </a>
      )}
    </div>
  );
}
