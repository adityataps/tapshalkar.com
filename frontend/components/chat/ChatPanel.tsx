"use client";

import { useState, useRef, useEffect } from "react";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import SuggestedPrompts from "./SuggestedPrompts";
import NodeChip from "./NodeChip";
import type { GraphNode } from "@/components/graph/types";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  onActiveNodesChange: (ids: string[]) => void;
  selectedNodes?: GraphNode[];
  onClearSelectedNodes?: () => void;
  onDeselectNode?: (id: string) => void;
  messages?: Message[];
  onMessagesChange?: (msgs: Message[]) => void;
  onNewChat?: () => void;
}

export default function ChatPanel({
  onActiveNodesChange,
  selectedNodes = [],
  onClearSelectedNodes,
  onDeselectNode,
  messages: propMessages,
  onMessagesChange,
  onNewChat,
}: Props) {
  const [internalMessages, setInternalMessages] = useState<Message[]>([]);
  const messages = propMessages ?? internalMessages;
  const setMessages = onMessagesChange
    ? (updater: Message[] | ((prev: Message[]) => Message[])) => {
        const next = typeof updater === "function" ? updater(messages) : updater;
        onMessagesChange(next);
      }
    : setInternalMessages;
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamingContent]);

  const sendMessage = async (text: string) => {
    if (isStreaming) return;

    // Context suffix is appended to the API message only; the UI shows the raw text
    const contextSuffix = selectedNodes.length > 0
      ? ` [context: ${selectedNodes.map((n) => n.label).join(", ")}]`
      : "";

    const uiMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(uiMessages);
    setIsStreaming(true);
    setStreamingContent("");
    onClearSelectedNodes?.();

    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    const apiMessages = [
      ...messages.map((m) => ({ role: m.role, content: m.content })),
      { role: "user", content: text + contextSuffix },
    ];

    try {
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: apiMessages }),
      });

      if (!response.ok || !response.body) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Something went wrong. Please try again." },
        ]);
        setIsStreaming(false);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value, { stream: true });
        const lines = raw.split("\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "text") {
              accumulated += event.delta;
              setStreamingContent(accumulated);
            } else if (event.type === "done") {
              onActiveNodesChange(event.activeNodeIds ?? []);
            } else if (event.type === "blocked") {
              accumulated = event.message;
              setStreamingContent(accumulated);
            }
          } catch {
            // incomplete JSON chunk — will arrive in next read
          }
        }
      }

      if (accumulated) {
        setMessages((prev) => [...prev, { role: "assistant", content: accumulated }]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setIsStreaming(false);
      setStreamingContent("");
    }
  };

  const showSuggestions = messages.length === 0 && !isStreaming;

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[#ef4444] text-xs tracking-[0.2em] uppercase">
          ask me anything
        </p>
        {messages.length > 0 && onNewChat && (
          <button
            onClick={onNewChat}
            className="font-mono text-[#444444] hover:text-[#f5f5f0] text-[9px] tracking-[0.15em] uppercase transition-colors"
          >
            new chat
          </button>
        )}
      </div>

      {showSuggestions && <SuggestedPrompts onSelect={sendMessage} />}

      {(messages.length > 0 || isStreaming) && (
        <div
          ref={threadRef}
          className="flex flex-col gap-4 flex-1 overflow-y-auto pr-2 min-h-0"
        >
          {messages.map((m, i) => (
            <ChatMessage key={i} role={m.role} content={m.content} />
          ))}
          {isStreaming && streamingContent && (
            <ChatMessage role="assistant" content={streamingContent} isStreaming />
          )}
        </div>
      )}

      {selectedNodes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedNodes.map((node) => (
            <NodeChip
              key={node.id}
              node={node}
              onRemove={onDeselectNode ?? (() => {})}
            />
          ))}
        </div>
      )}

      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
