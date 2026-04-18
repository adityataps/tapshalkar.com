# Chat Loading Indicator & Request Timeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `thinking... ▌` loading placeholder while the backend cold-starts, and abort requests that exceed 30 seconds.

**Architecture:** Both changes are isolated to `ChatPanel.tsx`. A derived `isWaiting` boolean (true when streaming but no content yet) drives the placeholder render. An `AbortController` per request fires after 30s and surfaces a specific timeout error message.

**Tech Stack:** React, TypeScript, Next.js (App Router, static export)

---

## Files

- Modify: `frontend/components/chat/ChatPanel.tsx`

---

### Task 1: Add 30s request timeout via AbortController

**Files:**
- Modify: `frontend/components/chat/ChatPanel.tsx:80-136`

- [ ] **Step 1: Add AbortController and timeout at the start of the try block**

  Replace the existing `try {` block opening and `fetch` call (lines 80–85) with:

  ```ts
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);

  try {
    const response = await fetch(`${apiUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: apiMessages }),
      signal: controller.signal,
    });
  ```

- [ ] **Step 2: Detect AbortError in the catch block**

  Replace the existing `catch` block (lines 128–132) with:

  ```ts
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
  ```

- [ ] **Step 3: Clear the timeout in the finally block**

  Replace the existing `finally` block (lines 133–136) with:

  ```ts
  } finally {
    clearTimeout(timeoutId);
    setIsStreaming(false);
    setStreamingContent("");
  }
  ```

- [ ] **Step 4: Verify TypeScript compiles**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Expected: no errors.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/components/chat/ChatPanel.tsx
  git commit -m "feat(chat): add 30s request timeout with abort controller"
  ```

---

### Task 2: Add `thinking... ▌` loading placeholder

**Files:**
- Modify: `frontend/components/chat/ChatPanel.tsx:139,159-171`

- [ ] **Step 1: Add `isWaiting` derived constant**

  After line 139 (`const showSuggestions = messages.length === 0 && !isStreaming;`), add:

  ```ts
  const isWaiting = isStreaming && !streamingContent;
  ```

- [ ] **Step 2: Add the waiting placeholder to the message thread**

  Replace lines 167–169 (the streaming message render):

  ```tsx
  {isStreaming && streamingContent && (
    <ChatMessage role="assistant" content={streamingContent} isStreaming />
  )}
  ```

  With:

  ```tsx
  {isWaiting && (
    <ChatMessage role="assistant" content="thinking..." isStreaming />
  )}
  {isStreaming && streamingContent && (
    <ChatMessage role="assistant" content={streamingContent} isStreaming />
  )}
  ```

  The `isStreaming` prop on `ChatMessage` appends the blinking `▌` cursor (see `ChatMessage.tsx:65`), so `thinking... ▌` renders automatically with no changes to `ChatMessage`.

- [ ] **Step 3: Verify TypeScript compiles**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Expected: no errors.

- [ ] **Step 4: Manual smoke test**

  ```bash
  cd frontend && npm run dev
  ```

  1. Open `http://localhost:3000`
  2. Send any message in the chat panel
  3. **Verify:** `thinking... ▌` appears immediately at the assistant position
  4. **Verify:** Once the first stream token arrives, `thinking... ▌` disappears and streaming text begins
  5. To test timeout: temporarily change `30_000` to `1` in `ChatPanel.tsx`, send a message, verify the timeout error message appears, then revert

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/components/chat/ChatPanel.tsx
  git commit -m "feat(chat): add thinking indicator during backend cold start"
  ```
