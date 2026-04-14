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
