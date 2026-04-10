"use client";

export default function SiteNav() {
  return (
    <nav className="sticky top-0 z-40 flex items-center justify-between px-8 py-4 bg-[#0d0d0d]/90 backdrop-blur border-b border-[#1a1a1a]">
      <a href="/" className="font-serif text-[#f5f5f0] text-sm tracking-wide">
        aditya tapshalkar
      </a>
      <div className="flex gap-6">
        <a href="#about" className="text-[#444444] hover:text-[#f5f5f0] text-sm transition-colors">
          About
        </a>
        <a href="#writing" className="text-[#444444] hover:text-[#f5f5f0] text-sm transition-colors">
          Writing
        </a>
      </div>
    </nav>
  );
}
