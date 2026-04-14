interface Props {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

export default function ChatMessage({ role, content, isStreaming = false }: Props) {
  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="bg-[#1a1a1a] border border-[#1e1e1e] text-[#f5f5f0] font-mono text-sm px-3 py-2 max-w-[70%]">
          {content}
        </div>
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
