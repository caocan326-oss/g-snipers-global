"use client";

import { useEffect, useState } from "react";

import { api, type UsageToday } from "@/lib/api";

export function UsageTodayBar({ meters, refreshToken = "" }: { meters: string[]; refreshToken?: string }) {
  const [data, setData] = useState<UsageToday | null>(null);
  const meterKey = meters.join(",");

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      api<UsageToday>("/api/usage/today")
        .then((next) => {
          if (!cancelled) setData(next);
        })
        .catch(() => undefined);
    };
    load();
    if (!refreshToken) {
      return () => {
        cancelled = true;
      };
    }
    const id = window.setInterval(load, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [meterKey, refreshToken]);

  if (!data) return null;
  const rows = data.meters.filter((item) => meters.includes(item.key));
  if (!rows.length) return null;

  return (
    <p className="text-xs leading-5 text-slate-500">
      今天已用：
      {rows.map((item, index) => (
        <span key={item.key}>
          {index ? " · " : ""}
          {item.label} {item.used}/{item.limit}
          {item.remaining <= 0 ? "（已用完）" : ""}
        </span>
      ))}
    </p>
  );
}
