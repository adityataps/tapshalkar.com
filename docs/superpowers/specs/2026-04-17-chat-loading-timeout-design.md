---
title: Chat Loading Indicator & Request Timeout
date: 2026-04-17
status: approved
---

# Chat Loading Indicator & Request Timeout

## Problem

The backend (Cloud Run, scales to zero) can take several seconds to cold-start. During this gap — between the user sending a message and the first SSE token arriving — the chat UI shows no feedback. The `fetch` call also has no timeout, so a stalled cold start hangs indefinitely.

## Scope

Changes are confined to `frontend/components/chat/ChatPanel.tsx`. No new components or files.

---

## Design

### 1. Loading State

A derived boolean captures the waiting gap:

```ts
const isWaiting = isStreaming && !streamingContent;
```

In the message thread, when `isWaiting` is true, render a `ChatMessage` with `role="assistant"` and `content="thinking..."` with `isStreaming={true}`. This reuses the existing blinking `▌` cursor already shown during streaming, placing it at the assistant message position immediately after the user sends.

Once the first stream token sets `streamingContent`, this placeholder is naturally superseded by the real streaming message — no special teardown needed.

**Copy:** `thinking...` — neutral, reads well for both cold-start delays and slow model responses.

### 2. Request Timeout

An `AbortController` is created at the start of each `sendMessage` call. A `setTimeout` of **30 seconds** calls `controller.abort()`. The `signal` is passed to `fetch`.

On abort, the `catch` block receives an `AbortError` and surfaces:

> `"Request timed out. The backend may be starting up — please try again."`

The timeout is cleared in `finally` to prevent firing after a successful response.

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
  // ...
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
```

---

## Render Logic Summary

| State | What renders in thread |
|---|---|
| `isStreaming=false` | Nothing (or existing messages) |
| `isWaiting` (`isStreaming=true`, `streamingContent=""`) | `ChatMessage` assistant with `"thinking... ▌"` |
| Streaming (`isStreaming=true`, `streamingContent` non-empty) | `ChatMessage` assistant with accumulated content + `▌` |

---

## Out of Scope

- Backend changes
- Retry logic
- Visual progress bars or spinners
- Timeout configuration (hardcoded at 30s)
