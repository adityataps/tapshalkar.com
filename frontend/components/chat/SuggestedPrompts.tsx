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
