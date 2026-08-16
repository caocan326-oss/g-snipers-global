import { FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { GeoPrompt, GeoTicket } from "@/lib/api";

import { diagnosisOptions, ticketStatus } from "../_helpers";

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
}: {
  tickets: GeoTicket[];
  prompts: GeoPrompt[];
  ticketForm: TicketForm;
  setTicketForm: (form: TicketForm) => void;
  addTicket: (e: FormEvent) => void;
  aiTicket: (id: string) => void;
  verifyTicket: (id: string, confirmed: boolean) => void;
  reopenTicket: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      {tickets.map((t) => (
        <Card key={t.id}>
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle className="text-base">{t.title}</CardTitle>
              <p className="mt-1 text-xs text-slate-500">
                诊断 {t.diagnosis_label} · {ticketStatus[t.status] ?? t.status}
              </p>
            </div>
            <Badge tone={t.status === "done" ? "green" : t.status === "reopened" ? "red" : "amber"}>
              {ticketStatus[t.status] ?? t.status}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-slate-600">理由：{t.rationale}</p>
            <p className="text-sm text-slate-600">验收：{t.acceptance_criteria}</p>
            {t.verified_note ? <p className="text-xs text-slate-500">备注：{t.verified_note}</p> : null}
            {t.evidence ? <pre className="whitespace-pre-wrap text-xs text-slate-500">{t.evidence}</pre> : null}
            {t.ai_review ? <p className="text-sm text-slate-600">初审：{t.ai_review}</p> : null}
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => aiTicket(t.id)}>
                AI 初审
              </Button>
              <Button size="sm" variant="outline" onClick={() => verifyTicket(t.id, false)}>
                未确认
              </Button>
              <Button size="sm" onClick={() => verifyTicket(t.id, true)}>
                确认验收
              </Button>
              <Button size="sm" variant="ghost" onClick={() => reopenTicket(t.id)}>
                复测后重开
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
      <Card>
        <CardHeader>
          <CardTitle>从问题生成整改项</CardTitle>
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
              placeholder="整改任务标题"
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
              placeholder="为什么需要整改"
              value={ticketForm.rationale}
              onChange={(e) => setTicketForm({ ...ticketForm, rationale: e.target.value })}
            />
            <Textarea
              placeholder="验收标准，例如：页面已补充可引用信息，并完成复测"
              value={ticketForm.acceptance_criteria}
              onChange={(e) => setTicketForm({ ...ticketForm, acceptance_criteria: e.target.value })}
            />
            <Button type="submit">创建整改项</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
