"use client";

import { useEffect, useState } from "react";

interface Currently {
  generated_at?: string;
  working_on?: { name: string; url: string }[];
  listening_to?: { artist: string; track: string; url: string };
  playing?: { name: string; hours: number; url: string };
  watching?: { title: string; season?: number; url?: string };
}

export default function CurrentlyBlock() {
  const [data, setData] = useState<Currently | null>(null);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/currently`)
      .then((r) => {
        if (!r.ok) return null;
        return r.json();
      })
      .then((d) => d && setData(d))
      .catch(() => {});
  }, []);

  if (!data) return null;

  return (
    <div className="mt-6">
      <p className="text-[#777777] text-xs uppercase tracking-widest mb-3">Currently</p>
      <div className="flex flex-col gap-2 text-sm">
        {data.working_on?.map((p) => (
          <Row key={p.name} label="Working on" value={p.name} url={p.url} />
        ))}
        {data.listening_to && (
          <Row
            label="Listening to"
            value={`${data.listening_to.artist} · ${data.listening_to.track}`}
            url={data.listening_to.url}
          />
        )}
        {data.playing && (
          <Row
            label="Playing"
            value={`${data.playing.name} · ${data.playing.hours}h`}
            url={data.playing.url}
          />
        )}
        {data.watching && (
          <Row
            label="Watching"
            value={data.watching.season ? `${data.watching.title} S${data.watching.season}` : data.watching.title}
            url={data.watching.url}
          />
        )}
      </div>
    </div>
  );
}

function Row({ label, value, url }: { label: string; value: string; url?: string }) {
  return (
    <div className="flex gap-3">
      <span className="text-[#777777] w-28 shrink-0">{label}</span>
      {url ? (
        <a href={url} target="_blank" rel="noopener noreferrer" className="text-[#f5f5f0] hover:text-[#ef4444] transition-colors">
          {value}
        </a>
      ) : (
        <span className="text-[#f5f5f0]">{value}</span>
      )}
    </div>
  );
}
