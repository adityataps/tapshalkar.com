# Phase 2d: Graph–Chat Integration Design

**Goal:** Unify the knowledge graph and chat into a single interactive surface. In full-screen mode, a persistent right-panel chat sidebar sits alongside the graph. Clicking graph nodes adds them as typed context chips to the chat input. Two distinct highlight states — cyan for user-selected nodes, red for agent-referenced nodes — make the two actors (human and AI) visually legible at a glance.

---

## Decisions Summary

| Question | Decision |
|---|---|
| Full-screen chat placement | Persistent right panel (~25% width), graph takes ~75% |
| Node click action | Adds chip to chat input; tooltip on chip hover shows node description |
| Node detail sidebar (GraphSidebar) | **Retired** — chips + tooltip replace it everywhere |
| Multi-select | Yes — clicking multiple nodes adds multiple chips |
| User-selected node color | Cyan `#22d3ee` |
| Agent-referenced node color | Red `#ef4444` (unchanged) |
| Chip type indicator | 6px colored dot using existing `NODE_COLORS` type palette |
| Chips after send | Clear after each message sent |
| Context in message | Appended as suffix: `"question text [context: Label1, Label2]"` |
| Architecture | Render prop (`rightPanel?: React.ReactNode`) on `GraphPanel` |

---

## Architecture

### State in `page.tsx`

```tsx
const [activeNodeIds, setActiveNodeIds] = useState<string[]>([]);   // agent-referenced (red)
const [selectedNodes, setSelectedNodes] = useState<GraphNode[]>([]); // user-selected (cyan)

const handleNodeSelect = (node: GraphNode) => {
  setSelectedNodes((prev) =>
    prev.some((n) => n.id === node.id)
      ? prev.filter((n) => n.id !== node.id)
      : [...prev, node]
  );
};

const handleActiveNodesChange = (ids: string[]) => {
  setActiveNodeIds(ids);
  setSelectedNodes([]); // agent response clears user selection
};
```

`page.tsx` passes:
- `GraphPanel`: `activeNodeIds`, `selectedNodeIds` (derived), `onNodeSelect`, `rightPanel`
- `ChatPanel`: `activeNodeIds` (for `onActiveNodesChange`), `selectedNodes`, `onClearSelectedNodes`

### `GraphPanel` render prop

`GraphPanel` keeps `expanded` state internally. When `expanded === true`, it renders the `rightPanel` slot:

```tsx
interface Props {
  activeNodeIds?: string[];
  selectedNodeIds?: string[];
  onNodeSelect?: (node: GraphNode) => void;
  rightPanel?: React.ReactNode;
}

// In the expanded overlay:
{expanded && (
  <div className="fixed inset-0 z-50 bg-[#0d0d0d] flex">
    <div className="flex-1 relative">{/* ForceGraph */}</div>
    <div className="w-[280px] border-l border-[#1e1e1e]">{rightPanel}</div>
  </div>
)}
```

`GraphSidebar` is removed entirely.

### `ForceGraph` node color priority

```tsx
const selectedSet = useMemo(() => new Set(selectedNodeIds), [selectedNodeIds]);

const nodeColor = useCallback(
  (node: GraphNode) => {
    if (selectedSet.has(node.id)) return "#22d3ee";   // user-selected
    if (activeSet.has(node.id)) return "#ef4444";      // agent-referenced
    return NODE_COLORS[node.type] ?? "#888";           // default
  },
  [selectedSet, activeSet]
);
```

### `NodeChip` component

```tsx
// frontend/components/chat/NodeChip.tsx
interface Props {
  node: GraphNode;
  onRemove: (id: string) => void;
}
```

Renders: `[type-dot] [label] [×]`. On hover, shows a tooltip with `node.description`. Uses CSS `position: relative` + `:hover` child for the tooltip — no JS state needed.

### `ChatPanel` context & chips

```tsx
interface Props {
  onActiveNodesChange: (ids: string[]) => void;
  selectedNodes: GraphNode[];
  onClearSelectedNodes: () => void;
}
```

Before sending, the message text is extended:
```tsx
const contextSuffix = selectedNodes.length > 0
  ? ` [context: ${selectedNodes.map((n) => n.label).join(", ")}]`
  : "";
const messageWithContext = text + contextSuffix;
```

After `fetch` is initiated (not after response), `onClearSelectedNodes()` is called and chips disappear immediately.

---

## Files Changed

| File | Action |
|---|---|
| `frontend/app/page.tsx` | Add `selectedNodes` state, `handleNodeSelect`, `handleActiveNodesChange`; pass `rightPanel` slot, `onNodeSelect`, `onClearSelectedNodes` |
| `frontend/components/graph/GraphPanel.tsx` | Add `rightPanel`, `selectedNodeIds`, `onNodeSelect` props; render rightPanel in expanded overlay; remove GraphSidebar import/usage |
| `frontend/components/graph/ForceGraph.tsx` | Add `selectedNodeIds` prop; three-color node logic |
| `frontend/components/chat/ChatPanel.tsx` | Add `selectedNodes`, `onClearSelectedNodes`; render chips; append context suffix; call `onClearSelectedNodes` on send |
| `frontend/components/chat/NodeChip.tsx` | **New**: type-dot + label + × + hover tooltip |
| `frontend/components/graph/GraphSidebar.tsx` | **Deleted** |

---

## Behaviour Rules

1. **Node click** → toggles in `selectedNodes`. Already-selected node deselects.
2. **Chip ×** → removes that node from `selectedNodes`.
3. **Send message** → context suffix appended, `onClearSelectedNodes()` called immediately (chips clear before response arrives).
4. **Agent responds** → `activeNodeIds` updated via `onActiveNodesChange`, which also calls `setSelectedNodes([])` in page.tsx.
5. **Color priority**: cyan (selected) > red (active) > type color (default). A node cannot visually be both simultaneously.
6. **`rightPanel` slot** renders only when `GraphPanel.expanded === true`. In the hero (non-expanded) view, chat remains in its own section below.

---

## Non-Goals

- No backend changes — context is appended client-side to the message string.
- No new API fields on `ChatRequest`.
- No animation on chip entry/exit (keep it simple).
- No persistence of selected nodes across page reloads.
