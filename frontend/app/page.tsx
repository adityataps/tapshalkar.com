"use client";

import { useState } from "react";
import GraphPanel from "@/components/graph/GraphPanel";
import ChatPanel, { type Message } from "@/components/chat/ChatPanel";
import type { GraphNode } from "@/components/graph/types";

export default function Home() {
  const [activeNodeIds, setActiveNodeIds] = useState<string[]>([]);
  const [agentZoomTrigger, setAgentZoomTrigger] = useState(0);
  const [selectedNodes, setSelectedNodes] = useState<GraphNode[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);

  const handleNodeSelect = (node: GraphNode) => {
    setSelectedNodes((prev) =>
      prev.some((n) => n.id === node.id)
        ? prev.filter((n) => n.id !== node.id)
        : [...prev, node]
    );
    setActiveNodeIds((prev) => prev.filter((id) => id !== node.id));
  };

  const handleDeselectNode = (id: string) => {
    setSelectedNodes((prev) => prev.filter((n) => n.id !== id));
  };

  const handleClearSelectedNodes = () => setSelectedNodes([]);

  const handleActiveNodesChange = (ids: string[]) => {
    setActiveNodeIds(ids);
    setSelectedNodes([]);
    setAgentZoomTrigger((n) => n + 1);
  };

  const handleNewChat = () => {
    setMessages([]);
    setActiveNodeIds([]);
    setSelectedNodes([]);
  };

  const chatProps = {
    onActiveNodesChange: handleActiveNodesChange,
    selectedNodes,
    onClearSelectedNodes: handleClearSelectedNodes,
    onDeselectNode: handleDeselectNode,
    messages,
    onMessagesChange: setMessages,
    onNewChat: handleNewChat,
  };

  return (
    <div>
      <section className="mx-auto max-w-6xl px-6 pt-6 lg:pt-14 pb-8">

        {/* Split hero */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center mb-8 lg:mb-12">

          {/* Left: text */}
          <div>
            <p className="font-mono text-[#ef4444] text-xs tracking-[0.2em] uppercase mb-4">
              ~/Aditya-Tapshalkar
            </p>
            <h1 className="font-serif text-5xl font-bold text-[#f5f5f0] leading-tight mb-4">
              I build systems<br />
              that <em className="text-[#ef4444] not-italic">think</em>.
            </h1>
            <p className="text-[#777777] text-sm leading-relaxed max-w-sm mb-8">
              Exploring language models, knowledge systems, and real-world product.
              Currently based in Atlanta, GA.
            </p>
            <div className="flex gap-3">
              {[
                { label: "github", href: "https://github.com/adityataps" },
                { label: "linkedin", href: "https://linkedin.com/in/adityatapshalkar" },
                { label: "resume", href: "/Resume_Aditya_Tapshalkar.pdf" },
                { label: "writing", href: "/blog" },
              ].map(({ label, href }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-xs border border-[#1e1e1e] text-[#777777] hover:text-[#ef4444] hover:border-[#ef4444] transition-colors px-3 py-1.5"
                >
                  {label}
                </a>
              ))}
            </div>
          </div>

          {/* Right: graph */}
          <div className="h-[420px] lg:h-[500px] flex flex-col gap-2">
            <GraphPanel
              activeNodeIds={activeNodeIds}
              agentZoomTrigger={agentZoomTrigger}
              selectedNodeIds={selectedNodes.map((n) => n.id)}
              onNodeSelect={handleNodeSelect}
              onDeselectAll={handleClearSelectedNodes}
              rightPanel={<ChatPanel {...chatProps} />}
            />
            <p className="font-mono text-[#555555] text-[9px] tracking-[0.15em] text-right">
              {selectedNodes.length > 0
                ? `${selectedNodes.length} node${selectedNodes.length > 1 ? "s" : ""} selected — included as context`
                : "click nodes to add context to your messages"}
            </p>
          </div>
        </div>

        <ChatPanel {...chatProps} />

      </section>
    </div>
  );
}
