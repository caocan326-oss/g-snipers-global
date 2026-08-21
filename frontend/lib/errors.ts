const NETWORK_HINTS = [
  "network is unreachable",
  "errno 101",
  "failed to connect",
  "name or service not known",
  "temporary failure in name resolution",
  "connection refused",
  "connecterror",
];

export function explainServiceError(message: string, kind: "speed" | "rank" | "generic" = "generic"): string {
  const text = (message || "").trim();
  if (!text) return text;
  const lower = text.toLowerCase();
  if (NETWORK_HINTS.some((hint) => lower.includes(hint))) {
    if (kind === "speed") {
      return "我们这边连不上测速服务，不是你电脑断网，也不代表官网挂了。";
    }
    if (kind === "rank") {
      return "我们这边连不上排名查询服务，不是你电脑断网，也不代表官网没有排名。";
    }
    return "我们这边连不上外部服务，不是你电脑断网。";
  }
  if (lower.includes("timed out") || lower.includes("timeout") || lower.includes("gateway time-out")) {
    return kind === "speed" ? "测速超时了，多半是中转或 Google 这边慢，请稍后再试。" : "查询超时了，请稍后再试。";
  }
  return text;
}
