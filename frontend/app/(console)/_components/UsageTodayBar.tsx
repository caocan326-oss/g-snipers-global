"use client";

import { useEffect, useState } from "react";

import { api, type UsageToday } from "@/lib/api";

export function UsageTodayBar({ meters }: { meters: string[] }) {
  const [data, setData] = useState<UsageToday | null>(null);

  useEffect(() => {
    api<UsageToday>("/api/usage/today")
      .then(setData)
      .catch(() => undefined);
  }, []);

  if (!data) return null;
  const rows = data.meters.filter((item) => meters.includes(item.key));
  if (!rows.length) return null;

  return (
    <p className="text-xs leading-5 text-slate-500">
      今天还剩：
      {rows.map((item, index) => (
        <span key={item.key}>
          {index ? " · " : ""}
          {item.label} {item.remaining}/{item.limit}
          {item.remaining <= 0 ? "（已用完）" : ""}
        </span>
      ))}
    </p>
  );
}
