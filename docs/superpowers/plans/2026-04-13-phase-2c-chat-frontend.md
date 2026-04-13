# Phase 2c: Chat Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-width chat section below the hero on the homepage. Users type questions, Claude streams responses word-by-word, and the force graph highlights nodes and edges referenced by the agent in real time.

**Architecture:** `page.tsx` lifts `activeNodeIds` state and passes it to both `GraphPanel` and `ChatPanel`. `ChatPanel` owns message state and SSE orchestration. `ForceGraph` derives active edges from `activeNodeIds` without any new prop. Four new components under `frontend/components/chat/`. SSE consumed via `fetch` + `ReadableStream` (not `EventSource` — that only supports GET).

**Tech Stack:** Next.js 16 (App Router, `output: 'export'`), TypeScript, React, Tailwind CSS

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/components/chat/SuggestedPrompts.tsx` | Create | Seed question chips, hidden after first message |
| `frontend/components/chat/ChatInput.tsx` | Create | Input field + send button, disabled while streaming |
| `frontend/components/chat/ChatMessage.tsx` | Create | Single message bubble with streaming text |
| `frontend/components/chat/ChatPanel.tsx` | Create | Section wrapper: message state, SSE loop, graph callback |
| `frontend/components/graph/ForceGraph.tsx` | Modify | Active edge highlighting derived from activeNodeIds |
| `frontend/app/page.tsx` | Modify | Lift activeNodeIds state, add ChatPanel section |

---

### Task 1: `SuggestedPrompts` component

**Files:**
- Create: `frontend/components/chat/SuggestedPrompts.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/components/chat/SuggestedPrompts.tsx
const PROMPTS = [
  "what are you working on?",
  "what's your tech stack?",
  "what do you do outside work?",
  "tell me about your background",
];

interface Props {
  onSelect: (prompt: string) => void;
}

export default function SuggestedPrompts({ onSelect }: Props) {
  return (
    <div className="flex gap-2 flex-wrap mb-5">
      {PROMPTS.map((p) => (
        <button
          key={p}
          onClick={() => onSelect(p)}
          className="border border-[#1e1e1e] text-[#444444] hover:text-[#f5f5f0] hover:border-[#444444] font-mono text-xs px-3 py-1.5 transition-colors"
        >
          {p}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Error|✓ Compiled"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/chat/SuggestedPrompts.tsx
git commit -m "feat(frontend): add SuggestedPrompts component"
```

---

### Task 2: `ChatInput` component

**Files:**
- Create: `frontend/components/chat/ChatInput.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/components/chat/ChatInput.tsx
"use client";

import { useState, KeyboardEvent } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled = false }: Props) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex gap-3 items-center border-t border-[#1e1e1e] pt-4">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKey}
        disabled={disabled}
        placeholder="ask something..."
        maxLength={500}
        className="flex-1 bg-transparent border-b border-[#333333] text-[#f5f5f0] font-mono text-sm py-1 outline-none placeholder-[#444444] disabled:opacity-40"
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className="font-mono text-xs border border-[#ef4444] text-[#ef4444] px-3 py-1.5 hover:bg-[#ef4444] hover:text-[#0d0d0d] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        send →
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | grep -E "error TS|✓ Compiled"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/chat/ChatInput.tsx
git commit -m "feat(frontend): add ChatInput component"
```

---

### Task 3: `ChatMessage` component

**Files:**
- Create: `frontend/components/chat/ChatMessage.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/components/chat/ChatMessage.tsx
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
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | grep -E "error TS|✓ Compiled"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/chat/ChatMessage.tsx
git commit -m "feat(frontend): add ChatMessage component with streaming cursor"
```

---

### Task 4: `ChatPanel` component

**Files:**
- Create: `frontend/components/chat/ChatPanel.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/components/chat/ChatPanel.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import SuggestedPrompts from "./SuggestedPrompts";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  onActiveNodesChange: (ids: string[]) => void;
}

export default function ChatPanel({ onActiveNodesChange }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages or streaming content changes
  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamingContent]);

  const sendMessage = async (text: string) => {
    if (isStreaming) return;

    const newMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setIsStreaming(true);
    setStreamingContent("");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";

    try {
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: newMessages.map((m) => ({ role: m.role, content: m.content })),
        }),
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
        // SSE chunks may contain multiple "data: {...}\n\n" lines
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

      // Commit streaming content as a real message
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
    <div className="flex flex-col gap-4">
      <p className="font-mono text-[#ef4444] text-xs tracking-[0.2em] uppercase">
        ask me anything
      </p>

      {showSuggestions && <SuggestedPrompts onSelect={sendMessage} />}

      {(messages.length > 0 || isStreaming) && (
        <div
          ref={threadRef}
          className="flex flex-col gap-4 max-h-80 overflow-y-auto pr-2"
        >
          {messages.map((m, i) => (
            <ChatMessage key={i} role={m.role} content={m.content} />
          ))}
          {isStreaming && streamingContent && (
            <ChatMessage role="assistant" content={streamingContent} isStreaming />
          )}
        </div>
      )}

      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | grep -E "error TS|✓ Compiled"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/chat/ChatPanel.tsx
git commit -m "feat(frontend): add ChatPanel with SSE streaming and message thread"
```

---

### Task 5: Active edge highlighting in `ForceGraph`

**Files:**
- Modify: `frontend/components/graph/ForceGraph.tsx`

The `activeNodeIds` prop already exists. We need to:
1. Derive an `activeSet` (`Set<string>`) from `activeNodeIds` via `useMemo`
2. Replace the static `linkColor={() => "#1e1e1e"}` with a callback that checks both endpoints

- [ ] **Step 1: Update `ForceGraph.tsx`**

```tsx
// In ForceGraph.tsx, after the nodeColor useCallback, add:

const activeSet = useMemo(() => new Set(activeNodeIds), [activeNodeIds]);

const linkColor = useCallback(
  (link: object) => {
    const l = link as { source: string | GraphNode; target: string | GraphNode };
    const src = typeof l.source === "string" ? l.source : (l.source as GraphNode).id;
    const tgt = typeof l.target === "string" ? l.target : (l.target as GraphNode).id;
    return activeSet.has(src) && activeSet.has(tgt) ? "#ef4444" : "#1e1e1e";
  },
  [activeSet]
);

// In the ForceGraph2D props, replace:
//   linkColor={() => "#1e1e1e"}
// with:
//   linkColor={linkColor}
```

The full updated `ForceGraph.tsx`:

```tsx
"use client";

import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";
import { useCallback, useRef, useState, useEffect, useMemo } from "react";

export interface GraphNode {
  id: string;
  type: "skill" | "project" | "experience" | "education" | "interest" | "health";
  label: string;
  description?: string;
  metadata?: Record<string, unknown>;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface Props {
  data: GraphData;
  activeNodeIds?: string[];
  onNodeClick?: (node: GraphNode) => void;
  graphRef?: React.MutableRefObject<ForceGraphMethods | undefined>;
}

const NODE_COLORS: Record<GraphNode["type"], string> = {
  skill:      "#3b82f6",
  project:    "#34d399",
  experience: "#a78bfa",
  education:  "#fbbf24",
  interest:   "#f472b6",
  health:     "#4ade80",
};

export default function ForceGraph({ data, activeNodeIds = [], onNodeClick, graphRef }: Props) {
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

  const graphData = useMemo(() => ({
    nodes: data.nodes.map((n) => ({ ...n })),
    links: data.edges.map((e) => ({ source: e.source, target: e.target, type: e.type, weight: e.weight })),
  }), [data]);

  const activeSet = useMemo(() => new Set(activeNodeIds), [activeNodeIds]);

  const nodeColor = useCallback(
    (node: GraphNode) =>
      activeSet.has(node.id) ? "#ef4444" : NODE_COLORS[node.type] ?? "#888",
    [activeSet]
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
          nodeRelSize={5}
          warmupTicks={150}
          linkColor={linkColor}
          linkWidth={(link: object) => ((link as GraphEdge).weight ?? 1) * 1.5}
          onNodeClick={onNodeClick as ((node: object) => void) | undefined}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | grep -E "error TS|✓ Compiled"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/graph/ForceGraph.tsx
git commit -m "feat(frontend): highlight active edges derived from activeNodeIds"
```

---

### Task 6: Wire `page.tsx`

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Update `page.tsx`**

The page must be a client component (we're adding `useState`). The old server component comment is removed.

```tsx
// frontend/app/page.tsx
"use client";

import { useState } from "react";
import GraphPanel from "@/components/graph/GraphPanel";
import ChatPanel from "@/components/chat/ChatPanel";

export default function Home() {
  const [activeNodeIds, setActiveNodeIds] = useState<string[]>([]);

  return (
    <div className="min-h-screen">
      {/* Split hero */}
      <section className="mx-auto max-w-6xl px-6 py-20 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center min-h-[calc(100vh-3rem)]">

        {/* Left: text */}
        <div>
          <p className="font-mono text-[#ef4444] text-xs tracking-[0.2em] uppercase mb-4">
            ~/Aditya-Tapshalkar
          </p>
          <h1 className="font-serif text-5xl font-bold text-[#f5f5f0] leading-tight mb-4">
            I build systems<br />
            that <em className="text-[#ef4444] not-italic">think</em>.
          </h1>
          <p className="text-[#444444] text-sm leading-relaxed max-w-sm mb-8">
            Exploring language models, knowledge systems, and real-world product.
            Currently based in Atlanta, GA.
          </p>
          <div className="flex gap-3">
            {[
              { label: "github", href: "https://github.com/adityataps" },
              { label: "linkedin", href: "https://linkedin.com/in/adityatapshalkar" },
              { label: "writing", href: "/blog" },
            ].map(({ label, href }) => (
              <a
                key={label}
                href={href}
                className="font-mono text-xs border border-[#1e1e1e] text-[#444444] hover:text-[#ef4444] hover:border-[#ef4444] transition-colors px-3 py-1.5"
              >
                {label}
              </a>
            ))}
          </div>
        </div>

        {/* Right: graph */}
        <div className="h-[420px] lg:h-[500px]">
          <GraphPanel activeNodeIds={activeNodeIds} />
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-[#1e1e1e]" />

      {/* Chat section */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <ChatPanel onActiveNodesChange={setActiveNodeIds} />
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles cleanly**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: clean build, all routes listed, no TypeScript errors

- [ ] **Step 3: Smoke test locally**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000`. Verify:
- Hero and graph render as before
- Chat section appears below the divider with "ASK ME ANYTHING" label
- Suggested prompts appear before any message is sent
- Prompts disappear after clicking one
- Input is disabled while a response would be streaming (test with a real backend or mock)

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(frontend): wire chat section and lifted activeNodeIds state in page.tsx"
```
