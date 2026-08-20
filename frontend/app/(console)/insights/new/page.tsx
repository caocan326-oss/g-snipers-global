"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Market } from "@/lib/api";

export default function NewMarketPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    region: "亚太",
    country_code: "",
    primary_locale: "en-US",
  });

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const created = await api<Market>("/api/markets", {
        method: "POST",
        body: JSON.stringify({ ...form, status: "watching" }),
      });
      router.replace(`/insights/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/insights" className="text-sm text-brand-700">
          ← 全部市场
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">新建目标市场</h1>
        <p className="mt-1 text-sm text-slate-500">记下国家、语言和区域，再补竞品和买家问题。</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>市场资料</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-2" onSubmit={onCreate}>
            <div>
              <Label>市场名称</Label>
              <Input className="mt-1" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="例如：美国" />
            </div>
            <div>
              <Label>国家代码</Label>
              <Input className="mt-1" value={form.country_code} onChange={(e) => setForm({ ...form, country_code: e.target.value })} required placeholder="例如：US" />
            </div>
            <div>
              <Label>区域</Label>
              <Input className="mt-1" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} />
            </div>
            <div>
              <Label>主要语言</Label>
              <Input className="mt-1" value={form.primary_locale} onChange={(e) => setForm({ ...form, primary_locale: e.target.value })} />
            </div>
            <div className="md:col-span-2">
              <Button type="submit">创建并打开</Button>
            </div>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
