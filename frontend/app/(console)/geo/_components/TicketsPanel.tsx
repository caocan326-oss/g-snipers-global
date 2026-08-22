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

export function TicketsPanel({
  tickets,
  prompts,
  ticketForm,
  setTicketForm,
  addTicket,
  aiTicket,
  verifyTicket,
  reopenTicket,
  setHandoff,
}: {
  tickets: GeoTicket[];
  prompts: GeoPrompt[];
  ticketForm: TicketForm;
  setTicketForm: (form: TicketForm) => void;
  addTicket: (e: FormEvent) => void;
  aiTicket: (id: string) => void;
  verifyTicket: (id: string, confirmed: boolean) => void;
  reopenTicket: (id: string) => void;
  setHandoff: (id: string, handoff: "drafted" | "sent" | "live", resultUrl?: string) => void;
}) {
  const [copied, setCopied] = useState("");
  const [liveUrls, setLiveUrls] = useState<Record<string, string>>({});
  return (
    <div className="space-y-4">
      {tickets.map((t) => (
        <Card key={t.id}>
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle className="text-base">{t.title}</CardTitle>
              <p className="mt-1 text-xs text-slate-500">
                判断 {diagnosisLabel[t.diagnosis] ?? t.diagnosis_label} · {ticketStatus[t.status] ?? t.status}
              </p>
              {t.sample_note ? <p className="mt-1 text-xs text-slate-700">这一轮 {t.sample_note}</p> : null}
              {t.handoff_label ? <p className="mt-1 text-xs font-medium text-slate-800">{t.handoff_label}</p> : null}
            </div>
            <Badge tone={t.status === "done" ? "green" : t.status === "reopened" ? "red" : "amber"}>
              {ticketStatus[t.status] ?? t.status}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-slate-600">理由：{t.rationale}</p>
            {t.customer_note ? (
              <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                <p className="text-xs font-medium text-slate-500">给客户的短稿</p>
                <pre className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-800">{t.customer_note}</pre>
              </div>
            ) : t.recommended_action ? (
              <p className="text-sm leading-6 text-slate-700">给客户：{t.recommended_action}</p>
            ) : null}
            <p className="text-sm text-slate-600">完成标准：{t.acceptance_criteria}</p>
            {t.retest_method ? <p className="text-sm text-slate-600">复查：{t.retest_method}</p> : null}
            {t.retest_result ? <p className="text-sm text-slate-700">复测记录：{t.retest_result}</p> : null}
            {t.verified_note ? <p className="text-xs text-slate-500">备注：{t.verified_note}</p> : null}
            {t.result_url ? (
              <p className="text-sm text-slate-700">
                客户上线地址：{" "}
                <a className="break-all text-brand-700 underline" href={t.result_url} target="_blank" rel="noreferrer">
                  {t.result_url}
                </a>
                <span className="ml-1 text-xs text-slate-400">登记地址，不是我们打开核对过的证明</span>
              </p>
            ) : null}
            <Input
              placeholder="客户已上线的页或帖地址，例如 https://www.ugreen.com/products/usa-65585"
              value={liveUrls[t.id] ?? t.result_url ?? ""}
              onChange={(e) => setLiveUrls((current) => ({ ...current, [t.id]: e.target.value }))}
            />
            {t.evidence ? <pre className="whitespace-pre-wrap text-xs text-slate-500">{t.evidence}</pre> : null}
            {t.ai_review ? <p className="text-sm text-slate-600">初审：{t.ai_review}</p> : null}
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
              <Button size="sm" variant={t.handoff === "drafted" ? "default" : "outline"} onClick={() => setHandoff(t.id, "drafted")}>
                已写改法
              </Button>
              <Button size="sm" variant={t.handoff === "sent" ? "default" : "outline"} onClick={() => setHandoff(t.id, "sent")}>
                已发给客户
              </Button>
              <Button
                size="sm"
                variant={t.handoff === "live" ? "default" : "outline"}
                onClick={() => setHandoff(t.id, "live", (liveUrls[t.id] ?? t.result_url ?? "").trim())}
              >
                客户已上线
              </Button>
              <Button size="sm" onClick={() => aiTicket(t.id)}>
                AI 初审
              </Button>
              <Button size="sm" variant="outline" onClick={() => verifyTicket(t.id, false)}>
                未确认
              </Button>
              <Button
                size="sm"
                onClick={() => verifyTicket(t.id, t.handoff === "live" && Boolean(t.result_url))}
                disabled={t.handoff !== "live" || !t.result_url}
              >
                确认完成
              </Button>
              <Button size="sm" variant="ghost" onClick={() => reopenTicket(t.id)}>
                复查后重开
              </Button>
            </div>
            <p className="text-[11px] text-slate-400">
              「客户已上线」必须先填页或帖地址。这是客户经理登记，不是我们打开核对过的证明。没到这一步、没有地址，不能验收，也不能再测。
            </p>
          </CardContent>
        </Card>
      ))}
      <Card>
        <CardHeader>
          <CardTitle>从问题生成待处理项</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={addTicket}>
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
              placeholder="完成标准，例如：对应页已上线或帖已发出，同一问再抽查一次。不要求这次必须提到。"
              value={ticketForm.acceptance_criteria}
              onChange={(e) => setTicketForm({ ...ticketForm, acceptance_criteria: e.target.value })}
            />
            <Button type="submit">创建待处理项</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
