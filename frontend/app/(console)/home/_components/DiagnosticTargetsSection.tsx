import { Plus, Target, X } from "lucide-react";

import { SiteSwitchBanner } from "@/components/SiteSwitchBanner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { ProjectTargets } from "@/lib/api";

import { DIAGNOSTIC_COUNTRIES, keywordPlaceholder, type TargetForm } from "../_helpers";

export type { TargetForm };

export function DiagnosticTargetsSection({
  targets,
  targetForm,
  setTargetForm,
  saveTargets,
  confirmSwitch,
  cancelSwitch,
  switchPending,
  saving,
  note,
  error,
}: {
  targets: ProjectTargets | null;
  targetForm: TargetForm;
  setTargetForm: (value: TargetForm) => void;
  saveTargets: () => void;
  confirmSwitch: () => void;
  cancelSwitch: () => void;
  switchPending: boolean;
  saving: boolean;
  note: string;
  error: string;
}) {
  function toggleCountry(code: string) {
    const country_codes = targetForm.country_codes.includes(code)
      ? targetForm.country_codes.filter((item) => item !== code)
      : [...targetForm.country_codes, code];
    setTargetForm({ ...targetForm, country_codes });
  }

  function updateCompetitor(index: number, patch: Partial<TargetForm["competitors"][number]>) {
    setTargetForm({
      ...targetForm,
      competitors: targetForm.competitors.map((row, i) => (i === index ? { ...row, ...patch } : row)),
    });
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Target className="h-5 w-5 text-brand-700" />
            <h2 className="text-lg font-semibold text-slate-950">客户诊断目标</h2>
            <Badge tone={targets?.readiness === "ready" ? "green" : "amber"}>{targets?.readiness === "ready" ? "可开跑" : "待补"}</Badge>
          </div>
          <p className="mt-1 text-sm text-slate-500">点国家、写买家会搜的词、填对手名字。国家码和语言不用人填。</p>
        </div>
        <Button type="button" onClick={saveTargets} disabled={saving || switchPending}>
          {saving ? "正在保存…" : "保存诊断目标"}
        </Button>
      </div>
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
      {switchPending ? (
        <div className="mt-3">
          <SiteSwitchBanner
            currentOrigin={targets?.site_origin || ""}
            nextOrigin={targetForm.site_origin.trim()}
            busy={saving}
            onConfirm={confirmSwitch}
            onCancel={cancelSwitch}
          />
        </div>
      ) : null}
      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1.2fr]">
        <div className="space-y-4">
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">客户名</div>
            <Input
              value={targetForm.tenant_name}
              onChange={(e) => setTargetForm({ ...targetForm, tenant_name: e.target.value })}
              placeholder="绿联 / UGREEN"
            />
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">官网</div>
            <Input
              value={targetForm.site_origin}
              onChange={(e) => setTargetForm({ ...targetForm, site_origin: e.target.value })}
              placeholder="https://www.example.com"
            />
            <p className="mt-1 text-xs text-slate-400">
              已保存：{targets?.site_origin || "还没有"}
              {targetForm.site_origin.trim() && targetForm.site_origin.trim() !== (targets?.site_origin || "")
                ? "。输入框里是还没保存的新地址。"
                : ""}
            </p>
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">目标国家</div>
            <div className="flex flex-wrap gap-2">
              {DIAGNOSTIC_COUNTRIES.map((country) => {
                const on = targetForm.country_codes.includes(country.code);
                return (
                  <button
                    key={country.code}
                    type="button"
                    onClick={() => toggleCountry(country.code)}
                    className={cn(
                      "rounded-md border px-3 py-1.5 text-sm",
                      on ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    )}
                  >
                    {country.name}
                  </button>
                );
              })}
            </div>
            {targetForm.extraMarkets.length ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {targetForm.extraMarkets.map((market) => (
                  <span key={`${market.code}-${market.name}`} className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600">
                    已有：{market.name}
                    <button
                      type="button"
                      aria-label={`去掉 ${market.name}`}
                      onClick={() =>
                        setTargetForm({
                          ...targetForm,
                          extraMarkets: targetForm.extraMarkets.filter((item) => item.code !== market.code || item.name !== market.name),
                        })
                      }
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">核心品类 / 搜索词</div>
            <Textarea
              className="min-h-[96px]"
              value={targetForm.keywords}
              onChange={(e) => setTargetForm({ ...targetForm, keywords: e.target.value })}
              placeholder={keywordPlaceholder(targetForm.site_origin, targetForm.tenant_name)}
            />
            <p className="mt-1 text-xs text-slate-400">
              灰字是示例，不是已保存的词。空着保存后，排名不会自己有词。搜索词不会编成买家问题；要抽查先记下原句。一行一个。日文词跟日本，英文词跟美英德澳。
            </p>
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">主要竞品</div>
            <div className="space-y-2">
              {targetForm.competitors.map((row, index) => (
                <div key={index} className="grid gap-2 sm:grid-cols-[1fr_1.2fr_auto]">
                  <Input
                    value={row.name}
                    onChange={(e) => updateCompetitor(index, { name: e.target.value })}
                    placeholder="对手名字"
                  />
                  <Input
                    value={row.website}
                    onChange={(e) => updateCompetitor(index, { website: e.target.value })}
                    placeholder="https:// 可选"
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setTargetForm({
                        ...targetForm,
                        competitors: targetForm.competitors.filter((_, i) => i !== index).length
                          ? targetForm.competitors.filter((_, i) => i !== index)
                          : [{ name: "", website: "" }],
                      })
                    }
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="mt-2"
              onClick={() => setTargetForm({ ...targetForm, competitors: [...targetForm.competitors, { name: "", website: "" }] })}
            >
              <Plus className="mr-1 h-3.5 w-3.5" />
              再加一个对手
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
