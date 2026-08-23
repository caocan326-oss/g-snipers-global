import { FormEvent, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { GeoPrompt, GeoTicket } from "@/lib/api";
import { copyText } from "@/lib/utils";

import { diagnosisLabel, diagnosisOptions, ticketStatus } from "../_helpers";

export type TicketForm = {
  prompt_id: string;
  title: string;
  diagnosis: string;
  rationale: string;
  acceptance_criteria: string;
};

function progressLine(t: GeoTicket): string {
  if ((t.retest_result || "").trim()) {
    return `再测已记：${t.retest_result.trim()}`;
  }
  if (t.handoff === "live" && (t.result_url || "").trim()) {
    return "已登记上线地址，可以同一问再测。登记地址不是我们打开核对过的证明。";
  }
  if ((t.customer_note || t.customer_paste || "").trim()) {
    return "短稿已可复制发给客户。";
  }
  return "先复制短稿给客户，改完再回来填地址。";
}

export function TicketsPanel({
  tickets,
  prompts,
  ticketForm,
  setTicketForm,
  addTicket,
  setHandoff,
  retestSameQuestions,
  canRetestSame,
  busyAction,
}: {
  tickets: GeoTicket[];
  prompts: GeoPrompt[];
  ticketForm: TicketForm;
  setTicketForm: (form: TicketForm) => void;
  addTicket: (e: FormEvent) => void;
  setHandoff: (id: string, handoff: "drafted" | "sent" | "live", resultUrl?: string) => void;
  retestSameQuestions: () => void;
  canRetestSame: boolean;
  busyAction: string;
}) {
  const [copied, setCopied] = useState("");
  const [liveUrls, setLiveUrls] = useState<Record<string, string>>({});

  return (
    <div className="space-y-4">
      {tickets.length === 0 ? (
        <Card>
          <CardContent className="py-6 text-sm text-slate-500">
            还没有待处理项。先抽查买家问题，系统会按「提到了 / 没给出官网」生成短稿。
          </CardContent>
        </Card>
      ) : null}

      {tickets.map((t) => {
        const liveUrl = (liveUrls[t.id] ?? t.result_url ?? "").trim();
        const canMarkLive = /^https?:\/\//i.test(liveUrl);
        const prompt = prompts.find((p) => p.id === t.prompt_id);
        return (
          <Card key={t.id}>
            <CardHeader className="flex flex-row items-start justify-between gap-3">
              <div className="min-w-0">
                <CardTitle className="text-base leading-6">{t.title}</CardTitle>
                {prompt?.prompt_text ? (
                  <p className="mt-2 text-sm text-slate-700">
                    老外问：<span className="font-medium">{prompt.prompt_text}</span>
                  </p>
                ) : null}
                <p className="mt-2 text-sm text-slate-700">
                  {t.sample_note
                    ? `这一轮：${t.sample_note}`
                    : `判断：${diagnosisLabel[t.diagnosis] ?? t.diagnosis_label}`}
                </p>
                <p className="mt-1 text-xs font-medium text-slate-800">{progressLine(t)}</p>
              </div>
              <Badge tone={t.status === "done" ? "green" : t.status === "reopened" ? "red" : "amber"}>
                {ticketStatus[t.status] ?? t.status}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
                <p className="text-xs font-medium text-slate-500">请改哪一页</p>
                {t.page_label || t.page_url ? (
                  <>
                    {t.page_label ? <p className="mt-1 text-sm text-slate-800">{t.page_label}</p> : null}
                    {t.page_url ? (
                      <a
                        className="mt-1 block break-all text-sm text-brand-700 underline"
                        href={t.page_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {t.page_url}
                      </a>
                    ) : null}
                  </>
                ) : (
                  <p className="mt-1 text-sm text-slate-500">短稿里会写建议页；还没有自动对应到站内页时，按短稿里的链接改。</p>
                )}
              </div>

              {(t.customer_note || t.recommended_action) && (
                <div className="rounded-md border border-amber-200 bg-amber-50/70 px-3 py-2">
                  <p className="text-xs font-medium text-slate-500">给客户的短稿</p>
                  <pre className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-800">
                    {t.customer_note || t.recommended_action}
                  </pre>
                </div>
              )}

              {t.retest_result ? (
                <p className="text-sm text-slate-700">
                  复测记录：{t.retest_result}
                  <span className="ml-1 text-xs text-slate-400">只记变没变，不承诺这次提到</span>
                </p>
              ) : null}

              <div className="space-y-2">
                <p className="text-xs font-medium text-slate-500">改完填上线地址</p>
                <Input
                  placeholder="例如 https://www.ugreen.com/products/usa-65585"
                  value={liveUrls[t.id] ?? t.result_url ?? ""}
                  onChange={(e) => setLiveUrls((current) => ({ ...current, [t.id]: e.target.value }))}
                />
                {t.result_url ? (
                  <p className="text-xs text-slate-500">
                    已登记：
                    <a className="ml-1 break-all text-brand-700 underline" href={t.result_url} target="_blank" rel="noreferrer">
                      {t.result_url}
                    </a>
                    （登记≠我们打开核对过）
                  </p>
                ) : null}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    const ok = await copyText(t.customer_paste || t.customer_note || t.recommended_action || "");
                    setCopied(ok ? t.id : "");
                  }}
                >
                  {copied === t.id ? "已复制" : "复制短稿"}
                </Button>
                <Button
                  size="sm"
                  disabled={!canMarkLive}
                  onClick={() => setHandoff(t.id, "live", liveUrl)}
                >
                  登记已上线
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => retestSameQuestions()}
                  disabled={!canRetestSame || !canMarkLive || busyAction === "retest-same"}
                >
                  {busyAction === "retest-same" ? "再测中…" : "同一问再测"}
                </Button>
              </div>
              <p className="text-[11px] text-slate-400">
                先复制短稿 → 客户改页 → 把上线链接填回来 → 再测同一问。再测只告诉你变没变。
              </p>
            </CardContent>
          </Card>
        );
      })}

      <details className="rounded-md border border-dashed border-slate-200 bg-slate-50/50 p-4">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">客户经理工具：手工建项</summary>
        <form className="mt-3 space-y-3" onSubmit={addTicket}>
          <select
            className="h-9 w-full rounded-md border border-slate-200 px-2 text-sm"
            value={ticketForm.prompt_id}
            onChange={(e) => setTicketForm({ ...ticketForm, prompt_id: e.target.value })}
            required
          >
            <option value="">选择买家问题</option>
            {prompts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.prompt_text}
              </option>
            ))}
          </select>
          <Input
            placeholder="待处理项标题"
            value={ticketForm.title}
            onChange={(e) => setTicketForm({ ...ticketForm, title: e.target.value })}
            required
          />
          <select
            className="h-9 w-full rounded-md border border-slate-200 px-2 text-sm"
            value={ticketForm.diagnosis}
            onChange={(e) => setTicketForm({ ...ticketForm, diagnosis: e.target.value })}
          >
            {diagnosisOptions.map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <Textarea
            placeholder="为什么需要处理"
            value={ticketForm.rationale}
            onChange={(e) => setTicketForm({ ...ticketForm, rationale: e.target.value })}
          />
          <Textarea
            placeholder="完成标准"
            value={ticketForm.acceptance_criteria}
            onChange={(e) => setTicketForm({ ...ticketForm, acceptance_criteria: e.target.value })}
          />
          <Button type="submit">创建待处理项</Button>
        </form>
      </details>
    </div>
  );
}
