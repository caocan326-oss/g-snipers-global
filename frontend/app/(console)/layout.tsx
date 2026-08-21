"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FileText, Globe2, LayoutDashboard, ListChecks, MapPinned, MessageSquare, Newspaper, SearchCheck, SquareCheckBig } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api, clearToken, getToken, type AiStatus, type User } from "@/lib/api";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/distribution", label: "客户说明", note: "搜不搜得到 / 这周改哪三处", icon: FileText },
  { href: "/home", label: "客户总览", note: "能否交付 / 风险 / 下一步", icon: LayoutDashboard },
  { href: "/onsite", label: "网站检查", note: "查看网页 / 给出改法 / 改后复查", icon: SearchCheck },
  { href: "/geo", label: "AI 搜索可见度", note: "有没有被提到 / 有没有给出官网", icon: Globe2 },
  { href: "/execution", label: "处理清单", note: "负责人 / 完成标准 / 复查", icon: SquareCheckBig },
  { href: "/offsite", label: "站外分发", note: "一个渠道一张卡片", icon: ListChecks },
];

const internalNav = [
  { href: "/insights", label: "市场机会", note: "国家 / 竞品 / 需求", icon: MapPinned },
  { href: "/seo", label: "SEO 内容", note: "选题 / 大纲 / 正文", icon: Newspaper },
  { href: "/inquiries", label: "询盘", note: "线索记录", icon: MessageSquare },
];

export default function ConsoleLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [ai, setAi] = useState<AiStatus | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<User>("/api/auth/me")
      .then((u) => {
        setUser(u);
        api<AiStatus>("/api/ai/status").then(setAi).catch(() => undefined);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  const allNav = [...nav, ...internalNav];
  const activeNav = allNav.find((item) => pathname === item.href || pathname.startsWith(item.href + "/")) ?? nav[0];

  return (
    <div className="min-h-screen bg-slate-100 lg:flex">
      <aside className="hidden w-72 flex-col border-r border-slate-900/10 bg-slate-950 text-white lg:flex">
        <div className="px-5 py-5">
          <div className="text-sm font-semibold tracking-wide">G-Snipers Global</div>
          <div className="mt-1 text-xs text-slate-400">海外获客诊断与执行平台</div>
          <div className="mt-4 rounded-md border border-white/10 bg-white/5 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">数据与 AI 状态</div>
            <div className="mt-1 flex items-center justify-between gap-2 text-xs">
              <span className="text-slate-300">AI 分析建议</span>
              <span className={cn("font-medium", ai?.configured ? "text-emerald-300" : "text-amber-300")}>{ai?.status ?? "…"}</span>
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex gap-3 rounded-md px-3 py-2.5 text-sm transition",
                active
                  ? "bg-white text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10 hover:text-white"
              )}
            >
              <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", active ? "text-brand-700" : "text-slate-500")} />
              <span className="min-w-0">
                <span className="block font-medium">{item.label}</span>
                <span className={cn("mt-0.5 block truncate text-xs", active ? "text-slate-500" : "text-slate-500")}>{item.note}</span>
              </span>
            </Link>
          )})}
          <div className="px-3 pt-4 text-[11px] uppercase tracking-wide text-slate-500">内部页</div>
          {internalNav.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex gap-3 rounded-md px-3 py-2.5 text-sm transition",
                active
                  ? "bg-white text-slate-950 shadow-sm"
                  : "text-slate-300 hover:bg-white/10 hover:text-white"
              )}
            >
              <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", active ? "text-brand-700" : "text-slate-500")} />
              <span className="min-w-0">
                <span className="block font-medium">{item.label}</span>
                <span className={cn("mt-0.5 block truncate text-xs", "text-slate-500")}>{item.note}</span>
              </span>
            </Link>
          )})}
        </nav>
        <div className="border-t border-white/10 px-4 py-4">
          <div className="text-[11px] uppercase tracking-wide text-slate-500">当前客户</div>
          <div className="mt-1 truncate text-sm font-medium text-white">{user?.tenant_name || "未选择客户"}</div>
          <p className="mt-1 text-xs leading-5 text-slate-400">你在看这家客户，不是被检查的人。</p>
          <div className="mt-2 truncate text-xs text-slate-500">
            {user?.name ?? "…"} · {user?.role === "admin" ? "管理员" : "客户经理"}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="mt-2 px-0 text-slate-400 hover:bg-transparent hover:text-white"
            onClick={() => {
              clearToken();
              router.replace("/login");
            }}
          >
            退出
          </Button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="border-b border-slate-200 bg-white lg:hidden">
          <div className="px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm font-semibold text-slate-950">当前客户：{user?.tenant_name || "未选择"}</div>
                <div className="mt-0.5 text-xs text-slate-500">{activeNav.label} · 你在看客户，不是被检查的人</div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  clearToken();
                  router.replace("/login");
                }}
              >
                退出
              </Button>
            </div>
            <nav className="-mx-1 mt-3 flex gap-2 overflow-x-auto pb-1">
              {allNav.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href || pathname.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "inline-flex h-10 shrink-0 items-center gap-1.5 rounded-md border px-3 text-sm font-medium",
                      active
                        ? "border-brand-600 bg-brand-50 text-brand-800"
                        : "border-slate-200 bg-white text-slate-600"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        </header>
        <main className="min-w-0 px-4 py-5 sm:px-5 lg:px-8 lg:py-6">{children}</main>
      </div>
    </div>
  );
}
