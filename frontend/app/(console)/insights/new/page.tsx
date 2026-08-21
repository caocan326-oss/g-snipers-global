"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { CountryPicker } from "@/components/CountryPicker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Market } from "@/lib/api";
import { countryByCode } from "@/lib/countries";

export default function NewMarketPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [countryCode, setCountryCode] = useState("US");

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    const country = countryByCode(countryCode);
    if (!country) return setError("请先点选一个国家。");
    try {
      const created = await api<Market>("/api/markets", {
        method: "POST",
        body: JSON.stringify({
          name: country.name,
          region: country.region,
          country_code: country.code,
          primary_locale: country.locale,
          status: "watching",
        }),
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
        <p className="mt-1 text-sm text-slate-500">点一个国家就行。国家码和语言不用填。</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>选国家</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onCreate}>
            <CountryPicker value={countryCode} onChange={setCountryCode} />
            <Button type="submit">创建并打开</Button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
