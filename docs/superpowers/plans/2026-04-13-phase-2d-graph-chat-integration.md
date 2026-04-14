# Phase 2d: Graph–Chat Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent chat sidebar to the full-screen graph view, multi-node context chip selection, and two-color node highlighting (cyan = user-selected, red = agent-referenced).

**Architecture:** `page.tsx` lifts `selectedNodes: GraphNode[]` state alongside the existing `activeNodeIds`. `GraphPanel` gains a `rightPanel?: React.ReactNode` render prop that is only rendered when expanded. `ForceGraph` gets a `selectedNodeIds` prop and three-color node logic. `ChatPanel` renders `NodeChip` components above the input and appends a context suffix to outgoing messages. `GraphSidebar` is deleted — chips + hover tooltips replace it everywhere.

**Tech Stack:** Next.js (App Router, static export), TypeScript, React, Tailwind CSS

---

## File Map

| File | Action |
|---|---|
| `frontend/components/chat/NodeChip.tsx` | Create — chip with type dot, label, ×, hover tooltip |
| `frontend/components/graph/ForceGraph.tsx` | Modify — export `NODE_COLORS`, add `selectedNodeIds` prop, three-color node logic |
| `frontend/components/graph/GraphPanel.tsx` | Modify — add `rightPanel`, `selectedNodeIds`, `onNodeSelect` props; render right panel when expanded; remove `GraphSidebar` |
| `frontend/components/graph/GraphSidebar.tsx` | Delete |
| `frontend/components/chat/ChatPanel.tsx` | Modify — add `selectedNodes`, `onClearSelectedNodes`, `onDeselectNode` props; render chips; append context suffix |
| `frontend/app/page.tsx` | Modify — lift `selectedNodes` state, wire all callbacks, pass `rightPanel` slot |

---

### Task 1: Export `NODE_COLORS` from `ForceGraph` and add `selectedNodeIds` prop

**Files:**
- Modify: `frontend/components/graph/ForceGraph.tsx`

- [ ] **Step 1: Update `ForceGraph.tsx`**

Replace the entire file with:

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
  selectedNodeIds?: string[];
  onNodeClick?: (node: GraphNode) => void;
  graphRef?: React.MutableRefObject<ForceGraphMethods | undefined>;
}

export const NODE_COLORS: Record<GraphNode["type"], string> = {
  skill:      "#3b82f6",
  project:    "#34d399",
  experience: "#a78bfa",
  education:  "#fbbf24",
  interest:   "#f472b6",
  health:     "#4ade80",
};

export default function ForceGraph({ data, activeNodeIds = [], selectedNodeIds = [], onNodeClick, graphRef }: Props) {
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
  const selectedSet = useMemo(() => new Set(selectedNodeIds), [selectedNodeIds]);

  const nodeColor = useCallback(
    (node: GraphNode) => {
      if (selectedSet.has(node.id)) return "#22d3ee";
      if (activeSet.has(node.id)) return "#ef4444";
      return NODE_COLORS[node.type] ?? "#888";
    },
    [selectedSet, activeSet]
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
git commit -m "feat(frontend): export NODE_COLORS, add selectedNodeIds prop with three-color node logic"
```

---

### Task 2: Create `NodeChip` component

**Files:**
- Create: `frontend/components/chat/NodeChip.tsx`

- [ ] **Step 1: Create `NodeChip.tsx`**

```tsx
// frontend/components/chat/NodeChip.tsx
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
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | grep -E "error TS|✓ Compiled"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/chat/NodeChip.tsx
git commit -m "feat(frontend): add NodeChip component with type dot and hover tooltip"
```

---

### Task 3: Update `GraphPanel` — render prop, remove `GraphSidebar`

**Files:**
- Modify: `frontend/components/graph/GraphPanel.tsx`
- Delete: `frontend/components/graph/GraphSidebar.tsx`

- [ ] **Step 1: Replace `GraphPanel.tsx`**

```tsx
// frontend/components/graph/GraphPanel.tsx
"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { ForceGraphMethods } from "react-force-graph-2d";
import type { GraphData, GraphNode } from "./ForceGraph";

const ForceGraph = dynamic(() => import("./ForceGraph"), { ssr: false });

const EMPTY_GRAPH: GraphData = { nodes: [], edges: [] };

interface Props {
  activeNodeIds?: string[];
  selectedNodeIds?: string[];
  onNodeSelect?: (node: GraphNode) => void;
  rightPanel?: React.ReactNode;
}

export default function GraphPanel({ activeNodeIds = [], selectedNodeIds = [], onNodeSelect, rightPanel }: Props) {
  const [data, setData] = useState<GraphData>(EMPTY_GRAPH);
  const [expanded, setExpanded] = useState(false);
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/graph`)
      .then((r) => { if (!r.ok) return null; return r.json(); })
      .then((d) => d && setData(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleReset = () => graphRef.current?.zoomToFit(400);

  const controls = (
    <div className="absolute bottom-4 left-4 z-10 flex gap-2">
      <button
        onClick={handleReset}
        className="text-[#444444] hover:text-[#f5f5f0] text-xs px-2 py-1 border border-[#444444] hover:border-[#f5f5f0] transition-colors"
        title="Reset view"
      >
        ↺
      </button>
      <button
        onClick={() => setExpanded((e) => !e)}
        className="text-[#444444] hover:text-[#f5f5f0] text-xs px-2 py-1 border border-[#444444] hover:border-[#f5f5f0] transition-colors"
        title={expanded ? "Collapse" : "Expand"}
      >
        {expanded ? "⊠" : "⤢"}
      </button>
    </div>
  );

  const graph = (
    <ForceGraph
      data={data}
      activeNodeIds={activeNodeIds}
      selectedNodeIds={selectedNodeIds}
      onNodeClick={onNodeSelect}
      graphRef={graphRef}
    />
  );

  if (expanded) {
    return (
      <div className="fixed inset-0 z-50 bg-[#0d0d0d] flex transition-all duration-300">
        <div className="flex-1 relative overflow-hidden">
          {controls}
          {graph}
        </div>
        {rightPanel && (
          <div className="w-[280px] border-l border-[#1e1e1e] flex-shrink-0 overflow-y-auto p-4">
            {rightPanel}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-[#0d0d0d] rounded-lg overflow-hidden border border-[#1e1e1e]">
      {controls}
      {graph}
    </div>
  );
}
```

- [ ] **Step 2: Delete `GraphSidebar.tsx`**

```bash
rm frontend/components/graph/GraphSidebar.tsx
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | grep -E "error TS|✓ Compiled"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 4: Commit**

```bash
git add frontend/components/graph/GraphPanel.tsx
git rm frontend/components/graph/GraphSidebar.tsx
git commit -m "feat(frontend): add rightPanel slot to GraphPanel, remove GraphSidebar"
```

---

### Task 4: Update `ChatPanel` — chips, context suffix, new props

**Files:**
- Modify: `frontend/components/chat/ChatPanel.tsx`

- [ ] **Step 1: Replace `ChatPanel.tsx`**

```tsx
// frontend/components/chat/ChatPanel.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import SuggestedPrompts from "./SuggestedPrompts";
import NodeChip from "./NodeChip";
import type { GraphNode } from "@/components/graph/ForceGraph";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  onActiveNodesChange: (ids: string[]) => void;
  selectedNodes?: GraphNode[];
  onClearSelectedNodes?: () => void;
  onDeselectNode?: (id: string) => void;
}

export default function ChatPanel({
  onActiveNodesChange,
  selectedNodes = [],
  onClearSelectedNodes,
  onDeselectNode,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
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
      <p className="font-mono text-[#ef4444] text-xs tracking-[0.2em] uppercase">
        ask me anything
      </p>

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
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | grep -E "error TS|✓ Compiled"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/chat/ChatPanel.tsx
git commit -m "feat(frontend): add node context chips and context suffix to ChatPanel"
```

---

### Task 5: Wire everything in `page.tsx`

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Replace `page.tsx`**

```tsx
// frontend/app/page.tsx
"use client";

import { useState } from "react";
import GraphPanel from "@/components/graph/GraphPanel";
import ChatPanel from "@/components/chat/ChatPanel";
import type { GraphNode } from "@/components/graph/ForceGraph";

export default function Home() {
  const [activeNodeIds, setActiveNodeIds] = useState<string[]>([]);
  const [selectedNodes, setSelectedNodes] = useState<GraphNode[]>([]);

  const handleNodeSelect = (node: GraphNode) => {
    setSelectedNodes((prev) =>
      prev.some((n) => n.id === node.id)
        ? prev.filter((n) => n.id !== node.id)
        : [...prev, node]
    );
  };

  const handleDeselectNode = (id: string) => {
    setSelectedNodes((prev) => prev.filter((n) => n.id !== id));
  };

  const handleClearSelectedNodes = () => setSelectedNodes([]);

  const handleActiveNodesChange = (ids: string[]) => {
    setActiveNodeIds(ids);
    setSelectedNodes([]); // agent response clears user selection
  };

  const chatProps = {
    onActiveNodesChange: handleActiveNodesChange,
    selectedNodes,
    onClearSelectedNodes: handleClearSelectedNodes,
    onDeselectNode: handleDeselectNode,
  };

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
          <GraphPanel
            activeNodeIds={activeNodeIds}
            selectedNodeIds={selectedNodes.map((n) => n.id)}
            onNodeSelect={handleNodeSelect}
            rightPanel={<ChatPanel {...chatProps} />}
          />
        </div>
      </section>

      {/* Scroll indicator */}
      <div className="flex justify-center pb-8 -mt-8">
        <div className="flex flex-col items-center gap-1 animate-bounce">
          <span className="font-mono text-[#444444] text-[10px] tracking-[0.2em] uppercase">ask me</span>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="text-[#444444]">
            <path d="M1 4l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-[#1e1e1e]" />

      {/* Chat section */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <ChatPanel {...chatProps} />
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Verify full build**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: clean build, all routes listed, no TypeScript errors.

- [ ] **Step 3: Smoke test locally**

```bash
cd frontend && npm run dev
```

Verify:
- Hero and graph render as before
- Click a node in the hero graph → node turns cyan, chip appears in the chat section below
- Click the same node again → deselects, chip removed
- Click × on chip → removes that chip
- Click ⤢ to expand graph → chat sidebar appears on the right
- Click a node in full-screen → chip appears in sidebar chat
- Type a message with chips selected → chips clear immediately when sent
- When agent responds → referenced nodes turn red, all cyan nodes clear

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(frontend): wire selectedNodes state and rightPanel slot in page.tsx"
```
