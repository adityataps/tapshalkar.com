import GraphPanel from "@/components/graph/GraphPanel";

export default function HeroSection() {
  return (
    <section className="flex flex-col md:flex-row min-h-[80vh]">
      <div className="flex flex-col justify-center px-8 md:px-16 py-16 md:w-1/2">
        <h1 className="font-serif text-4xl md:text-5xl text-[#f5f5f0] mb-4">
          Aditya Tapshalkar
        </h1>
        <p className="text-[#777777] text-lg leading-relaxed max-w-md">
          Software engineer. Building things at the intersection of systems and
          intelligence.
        </p>
      </div>
      <div className="md:w-1/2 min-h-[60vh] md:min-h-0">
        <GraphPanel />
      </div>
    </section>
  );
}
