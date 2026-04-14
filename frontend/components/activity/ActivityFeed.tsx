"use client";

import { useEffect, useState } from "react";

interface ActivityEvent {
  id: string;
  type: string;
  repo: string;
  repo_url: string;
  message?: string;
  created_at: string;
}

export default function ActivityFeed() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiUrl}/api/activity`)
      .then((r) => {
        if (!r.ok) return null;
        return r.json();
      })
      .then((d) => d && setEvents(d))
      .catch(() => {});
  }, []);

  if (events.length === 0) return null;

  return (
    <div>
      <p className="text-[#777777] text-xs uppercase tracking-widest mb-3">Recent activity</p>
      <div className="flex flex-col gap-3">
        {events.slice(0, 8).map((event) => (
          <div key={event.id} className="flex flex-col gap-0.5">
            <div className="flex items-baseline gap-2">
              <span className="text-[#777777] text-xs">{event.type}</span>
              <a
                href={event.repo_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#f5f5f0] text-sm hover:text-[#ef4444] transition-colors"
              >
                {event.repo}
              </a>
            </div>
            {event.message && (
              <p className="text-[#777777] text-xs truncate">{event.message}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
