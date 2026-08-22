"use client";

import { Download, HardDrive, Shield } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, downloadApiFile, type BackupCreate, type BackupStatus, type User } from "@/lib/api";

export default function BackupPage() {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api<BackupStatus>("/api/ops/backup")
      .then(setStatus)
      .catch((e) => setError(e instanceof Error ? e.message : "读不了副本状态"));
  }

  useEffect(() => {
    api<User>("/api/auth/me")
      .then((next) => {
        setUser(next);
        if (next.role !== "admin") {
          setError("只有管理员能看数据副本。");
          return;
        }
        load();
      })
      .catch((e) => setError(e instanceof Error ? e.message : "未登录"));
  }, []);

  async function exportNow() {
    setBusy(true);
    setError("");
    setNote("");
    try {
      const created = await api<BackupCreate>("/api/ops/backup", { method: "POST" });
      await downloadApiFile(`/api/ops/backup/${created.filename}`, created.filename);
      setNote(`已导出 ${created.filename}。异地：${created.offsite === "copied" ? "已抄走" : "没配或跳过"}。定时仍是关的。`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "导出失败");
    } finally {
      setBusy(false);
    }
  }

  if (user && user.role !== "admin") {
    return <p className="text-sm text-red-600">只有管理员能看这一页。</p>;
  }
  if (error && !status) return <p className="text-sm text-red-600">{error}</p>;
  if (!status) return <p className="text-sm text-slate-500">读取数据副本…</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="brand">管理员</Badge>
          <Badge tone={status.schedule_enabled ? "amber" : "green"}>{status.schedule_enabled ? "定时已开" : "定时关闭"}</Badge>
          <Badge tone={status.offsite_configured ? "green" : "amber"}>{status.offsite_configured ? "异地已配" : "异地未配"}</Badge>
        </div>
        <h1 className="mt-3 text-2xl font-semibold text-slate-950">客户数据副本</h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
          诊断历史、Fact Pack、竞品记录只在这一台库里。点导出下载一份；服务器每天还会自动打一份。
        </p>
        <div className="mt-4">
          <Button onClick={exportNow} disabled={busy}>
            <Download className="mr-2 h-4 w-4" />
            {busy ? "导出中…" : "导出一份并下载"}
          </Button>
        </div>
        {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="rounded-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-4 w-4" />
              导出落点
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-700">
            <p>本机目录：{status.local_dir}</p>
            <p>最多留 {status.keep} 份。</p>
            <p>异地方式：{status.offsite_kind === "none" ? "未配" : status.offsite_kind}</p>
            {status.offsite_dir ? <p>异地目录：{status.offsite_dir}</p> : null}
            {status.offsite_scp_set ? <p>SCP 目标已写在服务器环境变量里，页面不显示明文。</p> : null}
            <p className="text-slate-500">{status.note}</p>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              现在怎么用
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm leading-6 text-slate-600">
            <p>点上面「导出一份并下载」，浏览器会收下 json.gz。</p>
            <p>服务器每天还会自动打一份，不需要在这页再开开关。</p>
            <p>异地副本在家里/公司用拉取脚本拿，路径写在交接文档，不写在这页。</p>
          </CardContent>
        </Card>
      </section>

      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>已经打下的副本</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {status.dumps.length ? (
            status.dumps.map((item) => (
              <div key={item.filename} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm">
                <div>
                  <div className="font-medium text-slate-900">{item.filename}</div>
                  <div className="text-xs text-slate-500">
                    {(item.size_bytes / 1024).toFixed(1)} KB · {item.modified_at.slice(0, 19).replace("T", " ")} UTC
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => downloadApiFile(`/api/ops/backup/${item.filename}`, item.filename).catch((e) => setError(e instanceof Error ? e.message : "下载失败"))}
                >
                  下载
                </Button>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">还没有副本。点上面那一下就会在落点留下第一份。</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
