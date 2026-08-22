const NETWORK_HINTS = [
  "network is unreachable",
  "errno 101",
  "failed to connect",
  "name or service not known",
  "temporary failure in name resolution",
  "connection refused",
  "connecterror",
];

const TECHNICAL_HINTS = [
  "internal server error",
  "database is locked",
  "operationalerror",
  "sqlalchemy",
  "traceback",
  "failed to fetch",
  "networkerror",
  "econnreset",
  "errno ",
  "exception",
  "starlette",
  "uvicorn",
];

const HAS_CJK = /[\u4e00-\u9fff]/;

export const UNEXPECTED_FAILURE = "这次没办成，请再试一次。系统没有悄悄做完。";
export const SERVICE_UNAVAILABLE = "现在连不上服务，不是你的网络问题，请稍后再试。";

export function isAuthFailure(message: string): boolean {
  return /未登录|登录已失效|用户不存在/.test(message || "");
}

function looksTechnical(message: string): boolean {
  const lower = message.toLowerCase();
  return TECHNICAL_HINTS.some((hint) => lower.includes(hint));
}

export function explainRequestError(message: string, status?: number): string {
  const text = (message || "").trim();
  if (!status) {
    if (!text || looksTechnical(text)) return SERVICE_UNAVAILABLE;
    return text;
  }
  if (status >= 500) {
    if (HAS_CJK.test(text) && !looksTechnical(text)) return text;
    return UNEXPECTED_FAILURE;
  }
  if (!text || looksTechnical(text)) return UNEXPECTED_FAILURE;
  return text;
}

export function explainServiceError(message: string, kind: "speed" | "rank" | "generic" = "generic"): string {
  const text = (message || "").trim();
  if (!text) return explainRequestError(text);
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
  return explainRequestError(text);
}
