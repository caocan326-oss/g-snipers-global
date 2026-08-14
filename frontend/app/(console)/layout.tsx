"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api, clearToken, getToken, type User } from "@/lib/api";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/home", label: "首页" },
  { href: "/insights", label: "洞察投喂" },
  { href: "/onsite", label: "站内改页" },
  { href: "/geo", label: "GEO 闭环" },
  { href: "/offsite", label: "外链核验与分发" },
];

export default function ConsoleLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<User>("/api/auth/me")
      .then(setUser)
      .catch(() => router.replace("/login"));
  }, [router]);

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 flex-col border-r border-slate-200 bg-white">
        <div className="px-5 py-5">
          <div className="text-sm font-semibold text-brand-700">G-Snipers 海外版</div>
          <div className="mt-1 text-xs text-slate-500">三条交付链 · 人审后才动线上</div>
        </div>
        <nav className="flex-1 space-y-0.5 px-3">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block rounded-md px-3 py-2 text-sm",
                pathname === item.href || pathname.startsWith(item.href + "/")
                  ? "bg-brand-50 font-medium text-brand-700"
                  : "text-slate-600 hover:bg-slate-50"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="border-t border-slate-100 px-4 py-4">
          <div className="text-sm font-medium">{user?.name ?? "…"}</div>
          <div className="truncate text-xs text-slate-500">{user?.tenant_name}</div>
          <Button
            variant="ghost"
            size="sm"
            className="mt-2 px-0 text-slate-500"
            onClick={() => {
              clearToken();
              router.replace("/login");
            }}
          >
            退出
          </Button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-8">{children}</main>
    </div>
  );
}
