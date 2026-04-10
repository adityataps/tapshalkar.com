import SiteNav from "@/components/nav/SiteNav";
import HeroSection from "@/components/hero/HeroSection";
import AboutSection from "@/components/about/AboutSection";
import WritingSection from "@/components/writing/WritingSection";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0d0d0d]">
      <SiteNav />
      <HeroSection />
      <AboutSection />
      <WritingSection />
    </main>
  );
}
