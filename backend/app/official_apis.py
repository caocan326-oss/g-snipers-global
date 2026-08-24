"""Official channel APIs the customer uses themselves.

We do not hold a master key and do not auto-post. Each tenant jumps to the
official composer, or posts with their own OAuth / API token.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OfficialApi:
    platform_key: str
    label: str
    compose_url: str
    docs_url: str
    api_endpoint: str
    http_method: str
    auth_mode: str
    env_hint: str
    note: str


OFFICIAL_APIS: dict[str, OfficialApi] = {
    "linkedin_company": OfficialApi(
        platform_key="linkedin_company",
        label="LinkedIn",
        compose_url="https://www.linkedin.com/company/",
        docs_url="https://learn.microsoft.com/linkedin/marketing/community-management/shares/posts-api",
        api_endpoint="https://api.linkedin.com/rest/posts",
        http_method="POST",
        auth_mode="customer_oauth",
        env_hint="客户自己的 LinkedIn 应用 OAuth",
        note="用客户公司页授权。我们不代登、不群发。",
    ),
    "x_twitter": OfficialApi(
        platform_key="x_twitter",
        label="X",
        compose_url="https://x.com/compose/post",
        docs_url="https://docs.x.com/x-api/posts/create-post",
        api_endpoint="https://api.x.com/2/tweets",
        http_method="POST",
        auth_mode="customer_oauth",
        env_hint="客户自己的 X 开发者令牌",
        note="客户用自己的 App 发帖。禁止代发和自动刷帖。",
    ),
    "facebook_page": OfficialApi(
        platform_key="facebook_page",
        label="Facebook",
        compose_url="https://www.facebook.com/",
        docs_url="https://developers.facebook.com/docs/pages-api/posts",
        api_endpoint="https://graph.facebook.com/v21.0/{page-id}/feed",
        http_method="POST",
        auth_mode="customer_oauth",
        env_hint="客户主页 Page Token",
        note="跳到主页发，或客户用自己的 Page Token 调 Graph。",
    ),
    "instagram_business": OfficialApi(
        platform_key="instagram_business",
        label="Instagram",
        compose_url="https://www.instagram.com/",
        docs_url="https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing",
        api_endpoint="https://graph.facebook.com/v21.0/{ig-user-id}/media",
        http_method="POST",
        auth_mode="customer_oauth",
        env_hint="客户 Instagram 商业账户令牌",
        note="先跳到 App 发。接口发布要客户自己的商业账户授权。",
    ),
    "youtube_channel": OfficialApi(
        platform_key="youtube_channel",
        label="YouTube",
        compose_url="https://studio.youtube.com/",
        docs_url="https://developers.google.com/youtube/v3/docs/videos/insert",
        api_endpoint="https://www.googleapis.com/upload/youtube/v3/videos",
        http_method="POST",
        auth_mode="customer_oauth",
        env_hint="客户 Google Cloud OAuth",
        note="视频上传走客户自己的 YouTube 频道授权。",
    ),
    "tiktok_business": OfficialApi(
        platform_key="tiktok_business",
        label="TikTok",
        compose_url="https://www.tiktok.com/tiktokstudio",
        docs_url="https://developers.tiktok.com/doc/content-posting-api-get-started",
        api_endpoint="https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
        http_method="POST",
        auth_mode="customer_oauth",
        env_hint="客户 TikTok 开发者应用",
        note="短视频由客户自己的应用发布，不做自动刷量。",
    ),
    "pinterest_business": OfficialApi(
        platform_key="pinterest_business",
        label="Pinterest",
        compose_url="https://www.pinterest.com/pin-builder/",
        docs_url="https://developers.pinterest.com/docs/api/v5/pins-create",
        api_endpoint="https://api.pinterest.com/v5/pins",
        http_method="POST",
        auth_mode="customer_oauth",
        env_hint="客户 Pinterest 应用令牌",
        note="图针用客户自己的应用创建。",
    ),
}


def official_api_for(platform_key: str) -> OfficialApi | None:
    return OFFICIAL_APIS.get(platform_key or "")


def offsite_customer_ask(*, channel: str, body: str, compose_url: str = "") -> str:
    text = (body or "").strip()
    if not text:
        return ""
    name = (channel or "站外").strip() or "站外"
    parts = [f"请在「{name}」自己发这一条（我们不代发）：", text]
    url = (compose_url or "").strip()
    if url:
        parts.append(f"打开官方发帖页：{url}")
    parts.append("我们不代发、不代登。发完把帖子链接告诉我，我再回填。")
    return "\n\n".join(parts)


def official_api_payload(*, platform_key: str, title: str, body: str, target_url: str) -> dict:
    spec = official_api_for(platform_key)
    if spec is None:
        return {}
    text = (body or title or "").strip()
    return {
        "platform_key": spec.platform_key,
        "label": spec.label,
        "compose_url": spec.compose_url,
        "docs_url": spec.docs_url,
        "api_endpoint": spec.api_endpoint,
        "http_method": spec.http_method,
        "auth_mode": spec.auth_mode,
        "env_hint": spec.env_hint,
        "note": spec.note,
        "customer_body": {
            "text": text[:2000],
            "title": title,
            "link": target_url,
        },
    }
