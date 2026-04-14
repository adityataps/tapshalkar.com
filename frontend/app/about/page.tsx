const socials = [
  { label: "github", href: "https://github.com/adityataps" },
  { label: "linkedin", href: "https://linkedin.com/in/adityatapshalkar" },
  { label: "email", href: "mailto:aditya@tapshalkar.com" },
];

export default function About() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <p className="font-mono text-[#ef4444] text-xs tracking-widest uppercase mb-2">~/about</p>
      <h1 className="font-serif text-4xl font-bold text-[#f5f5f0] mb-8">About</h1>

      <div className="space-y-4 text-[#444444] text-sm leading-relaxed mb-12">
        <p>
          I&apos;m Aditya — an ML/AI engineer working at the intersection of language models,
          knowledge systems, and real-world product.
        </p>
        <p>
          Currently building tapshalkar.com. Previously various things.
        </p>
        <ul className="space-y-1 pt-2">
          {[
            "coffee addict",
            "swimmer",
            "homelab hobbyist",
            "cat dad of two cats",
          ].map((item) => (
            <li key={item} className="font-mono text-xs text-[#333333] before:content-['→_'] before:text-[#ef4444]">
              {item}
            </li>
          ))}
        </ul>
      </div>

      <h2 className="font-serif text-xl font-bold text-[#f5f5f0] mb-4">Links</h2>
      <div className="flex gap-3">
        {socials.map(({ label, href }) => (
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
  );
}
