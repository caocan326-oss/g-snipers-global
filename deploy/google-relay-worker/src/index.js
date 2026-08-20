const ALLOWED_HOSTS = new Set([
  "oauth2.googleapis.com",
  "www.googleapis.com",
  "searchconsole.googleapis.com",
  "pagespeedonline.googleapis.com",
]);

function unauthorized() {
  return new Response("unauthorized", { status: 401 });
}

function allowedIp(request, env) {
  const raw = (env.RELAY_ALLOW_IPS || "").trim();
  if (!raw) return true;
  const allowed = new Set(raw.split(",").map((item) => item.trim()).filter(Boolean));
  const ip = request.headers.get("cf-connecting-ip") || "";
  return allowed.has(ip);
}

export default {
  async fetch(request, env) {
    const key = request.headers.get("x-relay-key") || "";
    if (!env.RELAY_KEY || key !== env.RELAY_KEY) {
      return unauthorized();
    }
    if (!allowedIp(request, env)) {
      return new Response("forbidden", { status: 403 });
    }

    const target = request.headers.get("x-relay-target") || "";
    let url;
    try {
      url = new URL(target);
    } catch {
      return new Response("missing or bad x-relay-target", { status: 400 });
    }
    if (url.protocol !== "https:" || !ALLOWED_HOSTS.has(url.hostname)) {
      return new Response("target not allowed", { status: 403 });
    }

    const headers = new Headers();
    const authorization = request.headers.get("authorization");
    const contentType = request.headers.get("content-type");
    const accept = request.headers.get("accept");
    if (authorization) headers.set("authorization", authorization);
    if (contentType) headers.set("content-type", contentType);
    if (accept) headers.set("accept", accept);

    const init = { method: request.method, headers };
    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = await request.arrayBuffer();
    }

    const upstream = await fetch(url.toString(), init);
    return new Response(upstream.body, {
      status: upstream.status,
      headers: upstream.headers,
    });
  },
};
