import GraphPanel from "@/components/graph/GraphPanel";

// NOTE: page.tsx is a server component but does NOT fetch the graph.
// GraphPanel fetches client-side on mount — this is intentional to satisfy
// the static export constraint (no API calls during `next build`).
export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Split hero */}
      <section className="mx-auto max-w-6xl px-6 py-20 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center min-h-[calc(100vh-3rem)]">

        {/* Left: text */}
        <div>
          <p className="font-mono text-[#ef4444] text-xs tracking-[0.2em] uppercase mb-4">
            ~/ml-ai-engineer
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

        {/* Right: graph — fetches /api/graph client-side */}
        <div className="h-[420px] lg:h-[500px]">
          <GraphPanel />
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-[#1e1e1e]" />
    </div>
  );
}
