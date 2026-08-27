"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type WorkbenchItem } from "@/lib/api";

function TrendDots({ trend }: { trend: string }) {
  const rounds = (trend.split("轮：")[1] || "")
    .split("。")[0]
    .split("·")
    .map((part) => part.trim())
    .filter(Boolean);
  if (!rounds.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {rounds.map((note, index) => (
        <span
          key={`${note}-${index}`}
          className={`h-2.5 w-2.5 rounded-full ${note.includes("没提到") ? "bg-slate-300" : "bg-emerald-500"}`}
          title={note}
        />
      ))}
    </div>
  );
}

export function BuyerQuestionsSection({
  items,
  sources = [],
  competitors = [],
  trustNote = "",
  onRecorded,
}: {
  items: WorkbenchItem[];
  sources?: WorkbenchItem[];
  competitors?: WorkbenchItem[];
  trustNote?: string;
  onRecorded?: () => void;
}) {
  const [form, setForm] = useState({ prompt_text: "", recorded_from: "sales", source_note: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  async function recordQuestion(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNote("");
    setBusy(true);
    try {
      await api("/api/geo/prompts", {
        method: "POST",
        body: JSON.stringify({
          prompt_text: form.prompt_text.trim(),
          locale: "en-US",
          recorded_from: form.recorded_from,
          source_note: form.source_note.trim(),
        }),
      });
      setForm({ prompt_text: "", recorded_from: form.recorded_from, source_note: "" });
      setNote("已记下这句。没有抽过就空着，不会编。不保证这次被提到。");
      onRecorded?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "没记下");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="rounded-md border-sky-200">
      <CardContent className="space-y-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">AI 可见度作战室</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              同一批真问句：抽查看没看到、AI 引用了谁、提到了谁。测完出英文段，发给客户，他们贴上后再测同一问。没有原句就空着。不保证这次被提到。我们不代改。
            </p>
          </div>
          <Link href="/geo">
            <Button size="sm">
              去作战室
              <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>
        {items.length ? (
          <div className="space-y-2">
            {items.map((item) => (
              <Link
                key={item.id}
                href="/geo"
                className="block rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-500"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
                  {item.subtitle ? <span className="text-xs text-slate-500">{item.subtitle}</span> : null}
                </div>
                <h3 className="mt-2 text-sm font-medium text-slate-950">{item.title}</h3>
                {item.trend ? (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <TrendDots trend={item.trend} />
                    <p className="text-xs leading-5 text-slate-600">{item.trend}</p>
                  </div>
                ) : null}
                {item.meta ? <p className="mt-1 text-xs leading-5 text-slate-600">{item.meta}</p> : null}
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">还没有买家原句。先从销售、询盘、展会或客户自己说的记下来。搜索词不要记。没有原句就空着。</p>
        )}
        <form className="space-y-2 rounded-md border border-dashed border-slate-200 bg-slate-50 p-3" onSubmit={(event) => void recordQuestion(event)}>
          <p className="text-xs leading-5 text-slate-500">记下原句。搜索词不要记。不要编。</p>
          <Input
            placeholder="例如：Which factory can export industrial fasteners to the US?"
            value={form.prompt_text}
            onChange={(e) => setForm({ ...form, prompt_text: e.target.value })}
            required
          />
          <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <select
              className="h-9 rounded-md border border-slate-200 bg-white px-2 text-sm"
              value={form.recorded_from}
              onChange={(e) => setForm({ ...form, recorded_from: e.target.value })}
            >
              <option value="sales">销售听到的</option>
              <option value="inquiry">询盘里的</option>
              <option value="exhibition">展会听到的</option>
              <option value="customer">客户自己说的</option>
            </select>
            <Input
              placeholder="谁说的，可选"
              value={form.source_note}
              onChange={(e) => setForm({ ...form, source_note: e.target.value })}
            />
            <Button type="submit" size="sm" disabled={busy}>
              {busy ? "记下…" : "记下这句"}
            </Button>
          </div>
          {note ? <p className="text-xs text-emerald-700">{note}</p> : null}
          {error ? <p className="text-xs text-red-600">{error}</p> : null}
        </form>
        {trustNote ? <p className="text-sm leading-6 text-slate-600">{trustNote}</p> : null}
        {sources.length || competitors.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-950">AI 引用的站</h3>
              {sources.length ? (
                sources.map((item) => (
                  <div key={item.id} className="rounded-md border border-slate-200 bg-white p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
                      {item.subtitle ? <span className="text-xs text-slate-500">{item.subtitle}</span> : null}
                    </div>
                    <p className="mt-1 text-sm font-medium text-slate-950">{item.title}</p>
                    {item.meta ? <p className="mt-1 text-xs leading-5 text-slate-500">{item.meta}</p> : null}
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">还没有抽查引用。</p>
              )}
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-950">同一问里提到的竞品</h3>
              {competitors.length ? (
                competitors.map((item) => (
                  <div key={item.id} className="rounded-md border border-slate-200 bg-white p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
                      {item.subtitle ? <span className="text-xs text-slate-500">{item.subtitle}</span> : null}
                    </div>
                    <p className="mt-1 text-sm font-medium text-slate-950">{item.title}</p>
                    {item.meta ? <p className="mt-1 text-xs leading-5 text-slate-500">{item.meta}</p> : null}
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">抽查里还没有竞品名字。</p>
              )}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
