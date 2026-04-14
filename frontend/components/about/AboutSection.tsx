import CurrentlyBlock from "./CurrentlyBlock";
import ActivityFeed from "@/components/activity/ActivityFeed";

export default function AboutSection() {
  return (
    <section id="about" className="flex flex-col md:flex-row gap-12 px-8 md:px-16 py-16 border-t border-[#1a1a1a]">
      <div className="md:w-1/2">
        <h2 className="font-serif text-2xl text-[#f5f5f0] mb-4">About</h2>
        <p className="text-[#777777] leading-relaxed">
          I&apos;m a software engineer based in New York. I build systems that are fast,
          reliable, and occasionally interesting. Currently working on making this
          site a live reflection of what I&apos;m up to.
        </p>
        <CurrentlyBlock />
      </div>
      <div className="md:w-1/2">
        <ActivityFeed />
      </div>
    </section>
  );
}
