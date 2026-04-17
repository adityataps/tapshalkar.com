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
  contextNodes?: { id: string; label: string; type: string }[];
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

    const uiMessages: Message[] = [
      ...messages,
      {
        role: "user",
        content: text,
        contextNodes: selectedNodes.length > 0
          ? selectedNodes.map(({ id, label, type }) => ({ id, label, type }))
          : undefined,
      },
    ];
    setMessages(uiMessages);
    setIsStreaming(true);
    setStreamingContent("");
    onClearSelectedNodes?.();

    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    const apiMessages = [
      ...messages.map((m) => ({ role: m.role, content: m.content })),
      { role: "user", content: text + contextSuffix },
    ];

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30_000);

    try {
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: apiMessages }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        setMessages([
          ...uiMessages,
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
            } else if (event.type === "blocked" || event.type === "error") {
              accumulated = event.message;
              setStreamingContent(accumulated);
            }
          } catch {
            // incomplete JSON chunk — will arrive in next read
          }
        }
      }

      if (accumulated) {
        setMessages([...uiMessages, { role: "assistant", content: accumulated }]);
      }
    } catch (err) {
      const isTimeout = err instanceof Error && err.name === "AbortError";
      setMessages([
        ...uiMessages,
        {
          role: "assistant",
          content: isTimeout
            ? "Request timed out. The backend may be starting up — please try again."
            : "Something went wrong. Please try again.",
        },
      ]);
    } finally {
      clearTimeout(timeoutId);
      setIsStreaming(false);
      setStreamingContent("");
    }
  };

  const showSuggestions = messages.length === 0 && !isStreaming;
  const isWaiting = isStreaming && !streamingContent;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[#ef4444] text-xs tracking-[0.2em] uppercase">
          ask me anything
        </p>
        {messages.length > 0 && onNewChat && (
          <button
            onClick={onNewChat}
            className="font-mono text-[#777777] hover:text-[#f5f5f0] text-xs tracking-[0.15em] uppercase transition-colors border border-[#444444] hover:border-[#f5f5f0] px-3 py-1"
          >
            new chat
          </button>
        )}
      </div>

      {showSuggestions && <SuggestedPrompts onSelect={sendMessage} />}

      {(messages.length > 0 || isStreaming) && (
        <div
          ref={threadRef}
          className="flex flex-col gap-4 overflow-y-auto pr-2 max-h-[460px]"
        >
          {messages.map((m, i) => (
            <ChatMessage key={i} role={m.role} content={m.content} contextNodes={m.contextNodes} />
          ))}
          {isWaiting && (
            <ChatMessage role="assistant" content="thinking..." isStreaming />
          )}
          {isStreaming && streamingContent && (
            <ChatMessage role="assistant" content={streamingContent} isStreaming />
          )}
        </div>
      )}

      <ChatInput onSend={sendMessage} disabled={isStreaming} />

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
    </div>
  );
}
