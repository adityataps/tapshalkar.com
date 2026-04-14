"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/blog", label: "Writing" },
  { href: "/about", label: "About" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-[#1e1e1e] bg-[#0d0d0d]/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="font-mono text-xs text-[#ef4444] tracking-[0.2em] uppercase">
          ~/Aditya-Tapshalkar
        </Link>
        <div className="flex gap-6">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`font-mono text-xs tracking-widest uppercase transition-colors ${
                pathname.startsWith(href) ? "text-[#ef4444]" : "text-[#444444] hover:text-[#f5f5f0]"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
