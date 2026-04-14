import { NODE_COLORS } from "@/components/graph/types";

interface ContextNode {
  id: string;
  label: string;
  type: string;
}

interface Props {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  contextNodes?: ContextNode[];
}

export default function ChatMessage({ role, content, isStreaming = false, contextNodes }: Props) {
  if (role === "user") {
    return (
      <div className="flex flex-col items-end gap-1">
        <div className="bg-[#1a1a1a] border border-[#1e1e1e] text-[#f5f5f0] font-mono text-sm px-3 py-2 max-w-[70%]">
          {content}
        </div>
        {contextNodes && contextNodes.length > 0 && (
          <div className="flex flex-wrap justify-end gap-1">
            {contextNodes.map((n) => (
              <span
                key={n.id}
                className="inline-flex items-center gap-1 border border-[#2a2a2a] text-[#555555] font-mono text-[8px] px-1.5 py-0.5"
              >
                <span
                  className="w-1 h-1 rounded-full flex-shrink-0 opacity-60"
                  style={{ background: NODE_COLORS[n.type as keyof typeof NODE_COLORS] ?? "#555" }}
                />
                {n.label}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex gap-3 items-start">
      <span className="text-[#ef4444] font-mono text-xs mt-1 shrink-0">AT →</span>
      <p className="text-[#f5f5f0] font-mono text-sm leading-relaxed">
        {content}
        {isStreaming && (
          <span className="text-[#ef4444] animate-pulse">▌</span>
        )}
      </p>
    </div>
  );
}
